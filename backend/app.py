from flask import Flask, request, jsonify, logging
from flask_cors import CORS
import pymysql
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from sib_api_v3_sdk.rest import ApiException
from email_service import send_email
from dotenv import load_dotenv

load_dotenv()

mysql_password = os.getenv('MYSQL_PASSWORD')
access_key = os.getenv('ACCESS_KEY')
secret_access_key = os.getenv('SECRET_ACCESS_KEY')

s3 = boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)

app = Flask(__name__)
CORS(app)
app.config['MYSQL_HOST'] = 'us-cdbr-east-06.cleardb.net'
app.config['MYSQL_USER'] = 'b1a9c61d9610ec'
app.config['MYSQL_PASSWORD'] = mysql_password
app.config['MYSQL_DB'] = 'heroku_a2ad6038d6e7198'
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['BUCKET_NAME'] = 'dashvideobucket'


def get_db_connection():
    try:
        return pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            db=app.config['MYSQL_DB']
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None


def upload_to_aws(local_file, s3_file):
    try:
        s3.upload_file(local_file, app.config['BUCKET_NAME'], s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False


def create_presigned_url(object_name, expiration=3600):
    try:
        response = s3.generate_presigned_url('get_object',
                                             Params={'Bucket': app.config['BUCKET_NAME'],
                                                     'Key': object_name},
                                             ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    # The response contains the presigned URL
    return response


@app.route('/')
def index():
    return 'Dash Video Gallery'


@app.route('/upload', methods=['POST'])
def upload():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    if 'video' not in request.files:
        return jsonify({'error': 'No video file found'}), 400

    video = request.files['video']
    category = request.form.get('category')

    if video.filename == '':
        return jsonify({'error': 'No video file selected'}), 400

    cursor = conn.cursor()
    try:
        # Check if the filename already exists in the database
        cursor.execute("SELECT COUNT(*) FROM videos WHERE filename = %s", (video.filename,))
        count = cursor.fetchone()[0]

        if count > 0:
            return jsonify({'error': 'This video already exists.'}), 400

        # Save the uploaded file to the designated folder
        filename = video.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video.save(filepath)

        # Handle category
        cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (category,))
        cursor.execute("SELECT id FROM categories WHERE name = %s", (category,))
        category_id = cursor.fetchone()[0]

        # Save relevant information to the MySQL database
        cursor.execute("INSERT INTO videos (filename, filepath, category_id) VALUES (%s, %s, %s)",
                       (filename, filepath, category_id))
        conn.commit()

        # Return a response or perform additional actions
        return jsonify({'message': 'Video uploaded successfully', 'filename': filename})

    except Exception as e:
        print(e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/videos', methods=['GET'])
def get_videos():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor(pymysql.cursors.DictCursor)
    category = request.args.get('category', default=None, type=str)

    if category:
        # Fetch videos from specific category
        cursor.execute(
            "SELECT v.filename, c.name as category FROM videos v LEFT JOIN categories c ON v.category_id = c.id WHERE "
            "c.name = %s ORDER BY v.id DESC",
            (category,)
        )
    else:
        # Fetch all videos
        cursor.execute(
            "SELECT v.filename, c.name as category FROM videos v LEFT JOIN categories c ON v.category_id = c.id ORDER "
            "BY v.id DESC "
        )

    videos = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'videos': videos})


@app.route('/category', methods=['POST'])
def create_category():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    category_name = request.json.get('category_name')
    cursor = conn.cursor()
    cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (category_name,))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Category created successfully'}), 201


@app.route('/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT name FROM categories ORDER BY id DESC")
    categories = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({'categories': [category['name'] for category in categories]})


@app.route('/category/<category_name>', methods=['DELETE'])
def delete_category(category_name):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM categories WHERE name = %s", (category_name,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(e)
        return jsonify({'error': 'Database error'}), 500

    return jsonify({'message': 'Category deleted successfully'}), 200


@app.route('/video/<video_filename>', methods=['DELETE'])
def delete_video(video_filename):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor()
    try:
        # Delete video from the database
        cursor.execute("DELETE FROM videos WHERE filename = %s", (video_filename,))
        conn.commit()

        # Optionally, remove the file from the server
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        os.remove(filepath)

    except Exception as e:
        print(e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        cursor.close()
        conn.close()

    return jsonify({'message': 'Video deleted successfully'}), 200


@app.route('/sendEmail', methods=['POST'])
def sendEmail():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data received'}), 400

    email = data.get('recipient')  # change from 'email' to 'recipient'
    videos = data.get('videos')
    body = data.get('body')  # fetch the body from the request

    if not email or not videos:
        return jsonify({'error': 'Missing required information'}), 400

    # Upload videos to S3 and prepare URLs for the email.
    video_urls = []
    for video in videos:
        local_file_path = os.path.join(app.config['UPLOAD_FOLDER'], video)
        if upload_to_aws(local_file_path, video):
            url = create_presigned_url(video)
            if url is not None:
                # Format each URL as a clickable hyperlink in HTML
                url = "<a href='{}'>{}</a>".format(url, url)
                video_urls.append(url)

    # Prepare the email subject and content. Adjust these as needed.
    subject = "Your Videos"
    content = body + "<br><br>Here are your selected videos:<br>" + '<br><br>'.join(video_urls)  # include the body in the email content

    # Prepare the sender. This could also be adjusted as needed.
    sender = {"email": "techforgeconsulting@gmail.com"}

    try:
        # Attempt to send the email.
        send_email(sender, email, subject, content)
    except ApiException as e:
        return jsonify({'error': 'Failed to send email'}), 500

    return jsonify({'message': 'Email sent successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True)
