import boto3
import os
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve credentials
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_AUDIO_BUCKET = os.getenv("R2_AUDIO_BUCKET")
R2_IMAGE_BUCKET = os.getenv("R2_IMAGE_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")


# Ensure credentials exist
if not R2_ACCESS_KEY or not R2_SECRET_KEY:
    raise Exception("Cloudflare R2 credentials are missing! Check your .env file.")

# Initialize S3 client for Cloudflare R2
s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=boto3.session.Config(signature_version="s3v4")
)

response = s3_client.list_objects_v2(Bucket=R2_AUDIO_BUCKET)
print("📂 Audio Files in R2 Bucket:")
for obj in response.get("Contents", []):
    print(f"- {obj['Key']}")

response = s3_client.list_objects_v2(Bucket=R2_IMAGE_BUCKET)
print("📂 Image Files in R2 Bucket:")
for obj in response.get("Contents", []):
    print(f"- {obj['Key']}")

def upload_to_r2(file, is_audio=True):
    """Uploads an audio file to Cloudflare R2"""
    if not file:
        return None
    
    unique_filename = f"{uuid.uuid4()}-{file.filename}"
    bucket = R2_AUDIO_BUCKET if is_audio else R2_IMAGE_BUCKET  # ✅ Correct bucket selection


    try:
        s3_client.upload_fileobj(file.file, bucket, unique_filename)
        return f"{R2_ENDPOINT}/{bucket}/{unique_filename}"
    except Exception as e:
        print(f"⚠️ Error uploading to R2: {e}")
        return None

def generate_signed_url(bucket: str, file_key: str, expiration: int = 3600):
    """Generate a signed URL using SigV4 for private files stored in Cloudflare R2."""
    try:
        print(f"🔍 Generating signed URL for file key: {file_key}")  # ✅ Debugging output

        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": file_key},
            ExpiresIn=expiration,  # URL expires in 1 hour
        )

        print(f"🔗 Corrected Signed URL: {signed_url}")  # ✅ Debugging output
        return signed_url
    except Exception as e:
        print(f"⚠️ Error generating signed URL: {e}")
        return None
