import os
from minio import Minio
from minio.error import S3Error
from io import BytesIO
import json

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Default bucket name
DEFAULT_BUCKET = "chain-reaction"

def ensure_bucket_exists(bucket_name: str = DEFAULT_BUCKET):
    """Ensure the bucket exists, create if it doesn't"""
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
    except S3Error as e:
        print(f"Error ensuring bucket exists: {e}")
        raise

def upload_file(file_data: bytes, file_name: str, bucket_name: str = DEFAULT_BUCKET, content_type: str = "application/octet-stream"):
    """Upload a file to MinIO"""
    ensure_bucket_exists(bucket_name)
    
    try:
        result = minio_client.put_object(
            bucket_name,
            file_name,
            BytesIO(file_data),
            length=len(file_data),
            content_type=content_type
        )
        return {
            "bucket": bucket_name,
            "object_name": file_name,
            "etag": result.etag,
            "version_id": result.version_id
        }
    except S3Error as e:
        print(f"Error uploading file: {e}")
        raise

def download_file(file_name: str, bucket_name: str = DEFAULT_BUCKET):
    """Download a file from MinIO"""
    try:
        response = minio_client.get_object(bucket_name, file_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        print(f"Error downloading file: {e}")
        raise

def delete_file(file_name: str, bucket_name: str = DEFAULT_BUCKET):
    """Delete a file from MinIO"""
    try:
        minio_client.remove_object(bucket_name, file_name)
        return {"deleted": True, "object_name": file_name}
    except S3Error as e:
        print(f"Error deleting file: {e}")
        raise

def list_files(bucket_name: str = DEFAULT_BUCKET, prefix: str = "", recursive: bool = True):
    """List files in a bucket"""
    ensure_bucket_exists(bucket_name)
    
    try:
        objects = minio_client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
        return [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                "etag": obj.etag
            }
            for obj in objects
        ]
    except S3Error as e:
        print(f"Error listing files: {e}")
        raise

def get_file_info(file_name: str, bucket_name: str = DEFAULT_BUCKET):
    """Get information about a specific file"""
    try:
        stat = minio_client.stat_object(bucket_name, file_name)
        return {
            "name": stat.object_name,
            "size": stat.size,
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
            "etag": stat.etag,
            "content_type": stat.content_type,
            "metadata": stat.metadata
        }
    except S3Error as e:
        print(f"Error getting file info: {e}")
        raise