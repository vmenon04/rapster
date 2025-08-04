import boto3
import uuid
import os
from typing import Optional, Dict, List
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
    List contents of a bucket with optional prefix filter.
    
    Args:
        bucket: Name of the bucket to list
        prefix: Optional prefix to filter results
    
    Returns:
        List of object keys in the bucket
    """
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if 'Contents' not in response:
            return []
        
        objects = [obj['Key'] for obj in response['Contents']]
        logger.info(f"Listed {len(objects)} objects from bucket: {bucket}")
        return objects
        
    except Exception as e:
        logger.error(f"Error listing bucket contents: {e}")
        return []


def upload_hls_directory(local_dir: str, bucket_key_prefix: str, is_audio: bool = True) -> Optional[Dict[str, str]]:
    """
    Upload an entire HLS directory (master playlist, variant playlists, and segments) to R2.
    
    Args:
        local_dir: Local directory containing HLS files
        bucket_key_prefix: Prefix for R2 object keys (e.g., "audio/uuid/hls/")
        is_audio: Whether this is for audio bucket (True) or other bucket (False)
    
    Returns:
        Dictionary mapping local file paths to R2 URLs, or None if failed
    """
    if not os.path.exists(local_dir):
        logger.error(f"Local HLS directory does not exist: {local_dir}")
        return None
    
    bucket = settings.r2_audio_bucket if is_audio else settings.r2_image_bucket
    uploaded_files = {}
    
    try:
        # Walk through all files in the directory
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                
                # Calculate relative path from the base directory
                rel_path = os.path.relpath(local_file_path, local_dir)
                
                # Construct R2 key
                r2_key = f"{bucket_key_prefix.rstrip('/')}/{rel_path}"
                
                # Determine content type
                content_type = get_content_type_for_hls_file(file)
                
                # Upload file
                file_url = upload_file_to_r2(local_file_path, bucket, r2_key, content_type)
                if file_url:
                    uploaded_files[local_file_path] = file_url
                    logger.debug(f"Uploaded HLS file: {rel_path} -> {file_url}")
                else:
                    logger.error(f"Failed to upload HLS file: {rel_path}")
                    return None
        
        logger.info(f"Successfully uploaded {len(uploaded_files)} HLS files to R2")
        return uploaded_files
        
    except Exception as e:
        logger.error(f"Error uploading HLS directory: {e}")
        return None


def upload_file_to_r2(local_file_path: str, bucket: str, key: str, content_type: str = None) -> Optional[str]:
    """
    Upload a local file to R2 with specified key.
    
    Args:
        local_file_path: Path to local file
        bucket: R2 bucket name
        key: Object key in R2
        content_type: MIME type for the file
    
    Returns:
        Public URL of uploaded file, or None if failed
    """
    try:
        # Determine content type if not provided
        if not content_type:
            content_type = get_content_type_for_file(local_file_path)
        
        # Prepare upload arguments
        extra_args = {
            'ContentType': content_type,
            'Metadata': {
                'upload_type': 'hls_stream' if key.endswith(('.m3u8', '.ts')) else 'encoded_audio'
            }
        }
        
        # Set appropriate caching headers
        if key.endswith('.m3u8'):
            # Short cache for playlists (they can change)
            extra_args['CacheControl'] = 'public, max-age=30'
        elif key.endswith('.ts'):
            # Longer cache for segments (immutable)
            extra_args['CacheControl'] = 'public, max-age=86400'  # 1 day
        else:
            # Standard cache for other audio files
            extra_args['CacheControl'] = 'public, max-age=31536000'  # 1 year
        
        # Upload file
        s3_client.upload_file(local_file_path, bucket, key, ExtraArgs=extra_args)
        
        # Generate public URL
        file_url = f"{settings.r2_endpoint}/{bucket}/{key}"
        logger.debug(f"Uploaded file to R2: {key}")
        return file_url
        
    except Exception as e:
        logger.error(f"Failed to upload file to R2: {e}")
        return None


def get_content_type_for_hls_file(filename: str) -> str:
    """Get appropriate content type for HLS files."""
    if filename.endswith('.m3u8'):
        return 'application/vnd.apple.mpegurl'
    elif filename.endswith('.ts'):
        return 'video/mp2t'
    elif filename.endswith('.mp3'):
        return 'audio/mpeg'
    elif filename.endswith('.aac'):
        return 'audio/aac'
    else:
        return 'application/octet-stream'


def get_content_type_for_file(file_path: str) -> str:
    """Get content type based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.flac': 'audio/flac',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
        '.ogg': 'audio/ogg',
        '.m3u8': 'application/vnd.apple.mpegurl',
        '.ts': 'video/mp2t',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp'
    }
    return content_types.get(ext, 'application/octet-stream')


def upload_multiple_files(files_dict: Dict[str, str], bucket_key_prefix: str, is_audio: bool = True) -> Dict[str, str]:
    """
    Upload multiple files and return mapping of format names to URLs.
    
    Args:
        files_dict: Dictionary mapping format names to local file paths
        bucket_key_prefix: Prefix for R2 object keys
        is_audio: Whether this is for audio bucket
    
    Returns:
        Dictionary mapping format names to R2 URLs
    """
    uploaded_urls = {}
    bucket = settings.r2_audio_bucket if is_audio else settings.r2_image_bucket
    
    for format_name, local_path in files_dict.items():
        if not os.path.exists(local_path):
            logger.warning(f"File does not exist: {local_path}")
            continue
        
        # Generate R2 key
        file_ext = os.path.splitext(local_path)[1]
        r2_key = f"{bucket_key_prefix}{format_name}{file_ext}"
        
        # Upload file
        file_url = upload_file_to_r2(local_path, bucket, r2_key)
        if file_url:
            uploaded_urls[format_name] = file_url
        else:
            logger.error(f"Failed to upload {format_name} file")
    
    return uploaded_urls


# Initialize bucket verification on import


# Initialize bucket verification on import
try:
    if verify_bucket_access():
        logger.info("R2 service initialized successfully")
    else:
        logger.warning("R2 bucket access verification failed")
except Exception as e:
    logger.error(f"Failed to verify R2 access during initialization: {e}")
