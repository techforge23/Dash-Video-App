# Dash Video Gallery API Documentation

## Overview

The Dash Video Gallery API is a Flask-based web application designed to facilitate the management and sharing of video content. It integrates various services including AWS S3 for video storage, MySQL for database management, and Sendinblue for email notifications. This API enables users to upload videos, manage categories, fetch video lists, and share videos via email with generated presigned URLs for secure access.

## Configuration and Dependencies

- **Flask**: The core web application framework used to handle HTTP requests and responses.
- **Flask-CORS**: Enables Cross-Origin Resource Sharing (CORS) to allow web applications to make requests to the API from different domains.
- **PyMySQL**: A MySQL client library used to interact with the MySQL database for CRUD operations.
- **boto3**: The AWS SDK for Python, used to interact with AWS services like S3 for storing and retrieving video files.
- **sib_api_v3_sdk**: The SDK for Sendinblue's API, used for sending transactional emails.
- **Environment Variables**: Used to securely store sensitive information such as database password, AWS access key, and secret access key.

## Key Features

- **Database Connection**: Establishes a connection to a MySQL database to store and retrieve video and category data.
- **Video Upload and Management**: Allows users to upload videos to AWS S3 and record their metadata in the MySQL database. Provides functionality to delete videos and manage video categories.
- **Email Notifications**: Utilizes Sendinblue's API to send emails with links to videos. Uses presigned URLs for secure access to videos stored on AWS S3.
- **Category Management**: Supports creating, listing, and deleting video categories to organize content.
- **Error Handling**: Implements error handling for database connection issues, AWS S3 upload errors, and API exceptions.

## API Endpoints

- `GET /`: Returns a simple message indicating the API is operational.
- `POST /upload`: Handles video uploads, stores video metadata in the database, and uploads the video file to AWS S3.
- `GET /videos`: Fetches a list of videos, optionally filtered by category.
- `POST /category`: Creates a new video category.
- `GET /categories`: Lists all video categories.
- `DELETE /category/<category_name>`: Deletes a specified video category.
- `DELETE /video/<video_filename>`: Deletes a specified video from both the database and AWS S3.
- `POST /sendEmail`: Sends an email with links to selected videos using Sendinblue.

## Usage

1. **Environment Setup**: Ensure environment variables for MySQL and AWS credentials are set.
2. **Running the API**: Start the API server by executing the script. It listens on the configured port (default 5000).
3. **Interacting with the API**: Use HTTP requests to interact with the API endpoints for managing videos and categories, and for sending emails.

## Security and Best Practices

- **Sensitive Information**: The API uses environment variables to manage sensitive information, ensuring that database and AWS credentials are not hard-coded.
- **Error Handling**: Comprehensive error handling is implemented to provide clear feedback for failed operations, enhancing the API's reliability and usability.
- **CORS Configuration**: CORS is configured to control access to the API from web applications hosted on different domains.

## Conclusion

The Dash Video Gallery API is a robust solution for video content management and sharing, leveraging the power of AWS S3 for storage, MySQL for data persistence, and Sendinblue for email communications. Its Flask-based architecture and comprehensive feature set make it suitable for a wide range of video-sharing applications.
