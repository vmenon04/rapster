import boto3
import uuid
from typing import Optional
from fastapi import UploadFile
from app.config import get_settings
from app.logger import get_logger
from app.exceptions import FileUploadError, ConfigurationError

settings = get_settings()
logger = get_logger("r2_service")

# Validate configuration on import
if not all([settings.r2_access_key, settings.r2_secret_key, settings.r2_endpoint]):
    raise ConfigurationError("Cloudflare R2 credentials are missing! Check your .env file.")

# Initialize S3 client for Cloudflare R2
try:
    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key,
        aws_secret_access_key=settings.r2_secret_key,
        config=boto3.session.Config(signature_version="s3v4")
    )
    logger.info("Successfully initialized R2 client")
except Exception as e:
    logger.error(f"Failed to initialize R2 client: {e}")
    raise ConfigurationError(f"Failed to initialize R2 client: {e}")


def verify_bucket_access() -> bool:
    """Verify that we can access the configured buckets."""
    try:
        # Test audio bucket access
        s3_client.head_bucket(Bucket=settings.r2_audio_bucket)
        logger.info(f"Successfully verified access to audio bucket: {settings.r2_audio_bucket}")
        
        # Test image bucket access
        s3_client.head_bucket(Bucket=settings.r2_image_bucket)
        logger.info(f"Successfully verified access to image bucket: {settings.r2_image_bucket}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to verify bucket access: {e}")
        return False


def validate_file(file: UploadFile, is_audio: bool = True) -> None:
    """Validate file before upload."""
    if not file or not file.filename:
        raise FileUploadError("No file provided or file has no name")
    
    # Check file extension
    file_ext = file.filename.lower().split('.')[-1]
    if is_audio:
        allowed_formats = [fmt.lstrip('.') for fmt in settings.allowed_audio_formats]
        if file_ext not in allowed_formats:
            raise FileUploadError(
                f"Invalid audio format: .{file_ext}. "
                f"Allowed formats: {', '.join(settings.allowed_audio_formats)}"
            )
    else:
        allowed_formats = [fmt.lstrip('.') for fmt in settings.allowed_image_formats]
        if file_ext not in allowed_formats:
            raise FileUploadError(
                f"Invalid image format: .{file_ext}. "
                f"Allowed formats: {', '.join(settings.allowed_image_formats)}"
            )
    
    # Check file size (if we can get it)
    if hasattr(file, 'size') and file.size and file.size > settings.max_file_size:
        raise FileUploadError(
            f"File too large: {file.size} bytes. Maximum allowed: {settings.max_file_size} bytes"
        )

def upload_to_r2(file: UploadFile, is_audio: bool = True) -> Optional[str]:
    """
    Upload a file to Cloudflare R2 with validation and error handling.
    
    Args:
        file: The file to upload
        is_audio: Whether this is an audio file (True) or image file (False)
    
    Returns:
        The public URL of the uploaded file, or None if upload failed
    """
    if not file:
        return None
    
    try:
        # Validate the file
        validate_file(file, is_audio)
        
        # Generate unique filename
        file_ext = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Select appropriate bucket
        bucket = settings.r2_audio_bucket if is_audio else settings.r2_image_bucket
        
        logger.info(f"Uploading {'audio' if is_audio else 'image'} file: {file.filename} as {unique_filename}")
        
        # Reset file pointer to beginning
        file.file.seek(0)
        
        # Upload to R2
        # Sanitize filename to ASCII for S3 metadata
        import unicodedata
        def to_ascii(s):
            return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

        safe_filename = to_ascii(file.filename)
        s3_client.upload_fileobj(
            file.file, 
            bucket, 
            unique_filename,
            ExtraArgs={
                'ContentType': file.content_type or 'application/octet-stream',
                'Metadata': {
                    'original_filename': safe_filename,
                    'upload_type': 'audio' if is_audio else 'image'
                }
            }
        )
        
        # Generate the public URL
        file_url = f"{settings.r2_endpoint}/{bucket}/{unique_filename}"
        logger.info(f"Successfully uploaded file to: {file_url}")
        return file_url
        
    except FileUploadError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Error uploading file to R2: {e}")
        raise FileUploadError(f"Failed to upload file: {str(e)}")


def generate_signed_url(bucket: str, file_key: str, expiration: Optional[int] = None) -> Optional[str]:
    """
    Generate a signed URL for private file access with enhanced error handling.
    
    Args:
        bucket: The R2 bucket name
        file_key: The file key/path in the bucket
        expiration: URL expiration time in seconds (defaults to settings value)
    
    Returns:
        Signed URL string, or None if generation failed
    """
    try:
        if not bucket or not file_key:
            raise FileUploadError("Bucket name and file key are required")
        
        expiration = expiration or settings.signed_url_expiration
        
        logger.debug(f"Generating signed URL for bucket: {bucket}, key: {file_key}")

        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": file_key},
            ExpiresIn=expiration,
        )

        logger.debug(f"Successfully generated signed URL for {file_key}")
        return signed_url
        
    except Exception as e:
        logger.error(f"Error generating signed URL for {file_key}: {e}")
        raise FileUploadError(f"Failed to generate signed URL: {str(e)}")


def delete_file_from_r2(bucket: str, file_key: str) -> bool:
    """
    Delete a file from R2 storage.
    
    Args:
        bucket: The R2 bucket name
        file_key: The file key/path to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not bucket or not file_key:
            logger.error("Bucket name and file key are required for deletion")
            return False
        
        logger.info(f"Deleting file from R2: {bucket}/{file_key}")
        
        s3_client.delete_object(Bucket=bucket, Key=file_key)
        logger.info(f"Successfully deleted file: {bucket}/{file_key}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting file {file_key} from bucket {bucket}: {e}")
        return False


def list_bucket_contents(bucket: str, prefix: str = "") -> list:
    """
    List contents of an R2 bucket.
    
    Args:
        bucket: The bucket name
        prefix: Optional prefix to filter objects
    
    Returns:
        List of object keys
    """
    try:
        logger.info(f"Listing contents of bucket: {bucket}")
        
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        objects = []
        for page in pages:
            if 'Contents' in page:
                objects.extend([obj['Key'] for obj in page['Contents']])
        
        logger.info(f"Found {len(objects)} objects in bucket {bucket}")
        return objects
        
    except Exception as e:
        logger.error(f"Error listing bucket contents: {e}")
        return []


# Initialize bucket verification on import
try:
    if verify_bucket_access():
        logger.info("R2 service initialized successfully")
    else:
        logger.warning("R2 bucket access verification failed")
except Exception as e:
    logger.error(f"Failed to verify R2 access during initialization: {e}")
