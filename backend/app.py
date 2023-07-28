import sib_api_v3_sdk
from flask import Flask, request, jsonify, logging
from flask_cors import CORS
import pymysql
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from sib_api_v3_sdk.rest import ApiException
from io import BytesIO


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


def upload_to_aws(file_obj, s3_file):
    try:
        s3.upload_fileobj(file_obj, app.config['BUCKET_NAME'], s3_file)
        print("Upload Successful")
        return True
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


def send_email(sender, recipient, subject, content):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = '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'
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender=sender,
        to=[{"email": recipient}],
        subject=subject,
        html_content=content
    )

    try:
        api_response = api_instance.send_transac_email(email)
        print(api_response)
    except ApiException as e:
        print("Exception when calling TransactionalEmailsApi->send_transac_email: %s\n" % e)


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

        # Upload the video file to S3
        video_file = BytesIO(video.read())
        upload_to_aws(video_file, video.filename)

        # Handle category
        cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (category,))
        cursor.execute("SELECT id FROM categories WHERE name = %s", (category,))
        category_id = cursor.fetchone()[0]

        # Save relevant information to the MySQL database
        cursor.execute("INSERT INTO videos (filename, category_id) VALUES (%s, %s)",
                       (video.filename, category_id))
        conn.commit()

        # Return a response or perform additional actions
        return jsonify({'message': 'Video uploaded successfully', 'filename': video.filename})

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

        # Remove the file from S3
        try:
            s3.delete_object(Bucket=app.config['BUCKET_NAME'], Key=video_filename)
            print("Deletion from S3 Successful")
        except Exception as e:
            print("Error deleting from S3: ", e)
            return jsonify({'error': 'Error deleting from S3'}), 500

    except Exception as e:
        print(e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        cursor.close()
        conn.close()

    return jsonify({'message': 'Video deleted successfully'}), 200


@app.route('/sendEmail', methods=['POST'])
def sendEmail():
    missing_fields = [field for field in ['recipient', 'body', 'videos'] if field not in request.form]
    if missing_fields:
        return jsonify({'error': f"Missing required information: {', '.join(missing_fields)}"}), 400

    recipient = request.form.get('recipient')
    body = request.form.get('body')
    videos = request.form.get('videos').split(',')  # Splitting filenames by comma

    video_urls = []
    for video_filename in videos:  # Loop over filenames, not file objects
        try:
            url = create_presigned_url(video_filename.strip())  # Remove leading/trailing spaces
            if url is not None:
                # Format each URL as a clickable hyperlink in HTML
                url = "<a href='{}'>{}</a>".format(url, url)
                video_urls.append(url)
        except Exception as e:
            print("Error generating presigned URL: ", e)
            return jsonify({'error': 'Error generating presigned URL'}), 500

    # Prepare the email subject and content. Adjust these as needed.
    subject = "Your Dash Videos"
    content = body + "<br><br>Here are your selected videos:<br>" + '<br><br>'.join(video_urls)  # include the body in the email content

    # Prepare the sender. This could also be adjusted as needed.
    sender = {"email": "techforgeconsulting@gmail.com"}

    try:
        # Attempt to send the email.
        send_email(sender, recipient, subject, content)
    except ApiException as e:
        return jsonify({'error': 'Failed to send email'}), 500

    return jsonify({'message': 'Email sent successfully'}), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))  # Default port is 5000 if PORT is not set
    app.run(debug=True, host='0.0.0.0', port=port)

