# Backend

This is the backend service for a music-sharing application. It enables users to upload audio files, extract musical features (like key, scale, BPM) using [Essentia](https://essentia.upf.edu/), and store both the files and metadata securely using **Cloudflare R2** and **Supabase**.

---

## Design Overview

### Features
- **Audio Analysis:** Uses Essentia to extract BPM, key, and scale.
- **Cloud Storage:** Files (audio/images) stored on Cloudflare R2 with signed URL access.
- **Metadata Database:** Supabase stores audio metadata.
- **Signed URLs:** Time-limited access to files via AWS S3-compatible URLs.
- **Dockerized:** Reproducible and portable environment with Docker.
- **FastAPI:** High-performance backend with async I/O.

### Folder Structure

```
backend/
├── app/
│   ├── main.py               # Entry point for FastAPI app
│   ├── crud.py               # Handles DB interactions (Supabase)
│   ├── schemas.py            # Pydantic models for validation
│   ├── routes/               # All API endpoints
│   └── services/             # External integrations (R2, ML)
├── .env                      # Environment variables (not committed)
├── Dockerfile                # Builds the backend image
├── docker-compose.yml        # Orchestrates backend service
├── requirements.txt          # Python dependencies
└── .dockerignore             # Files to exclude from Docker image
```

---

## How to Run Locally

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)
- (Optional) Python 3.9+ if running outside Docker

---

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/music_app.git
cd music_app/backend
```

---

### 2. Set Up Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Fill in with:
- Supabase credentials (URL + anon/public key)
- Cloudflare R2 credentials
- Bucket names and R2 endpoint

**Do not commit this file**

---

### 3. Build & Run with Docker

```bash
docker-compose up --build
```

This will:
- Build the FastAPI backend
- Compile Essentia from source
- Mount your code into the container
- Start the server on `http://localhost:8000`

---

### 4. Test It Out

- API Root: [http://localhost:8000](http://localhost:8000)
- Interactive Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Upload Audio: `POST /audio/upload/`
- Analyze Only: `POST /audio/analyze/`
- List Audio: `GET /audio/list-audio/`

---

## Example `.env`

```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

R2_ACCESS_KEY=your-r2-access-key
R2_SECRET_KEY=your-r2-secret-key
R2_AUDIO_BUCKET=your-audio-bucket-name
R2_IMAGE_BUCKET=your-image-bucket-name
R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
```

---

## Developer Notes

- File uploads are temporarily saved locally during analysis.
- Audio metadata includes BPM, key, scale, title, artist, and file/image URLs.
- Uses Python’s `uuid` to avoid filename collisions in R2.
- Can be extended with Redis/RQ for background task processing (already in `requirements.txt`).

---

## 📬 Contact

For questions or contributions, reach out to [@vmenon04](https://github.com/vmenon04) or open an issue!

---
