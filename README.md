📄 README — PDF to JSON Converter
--------------------------------------

🛠️ Build Docker Image:

docker build --platform linux/amd64 -t pdf-json-extractor .

▶️ Run the Docker Container:

docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-json-extractor

✅ This will:
- Read PDFs from /input
- Generate .json output in /output

📁 Project Structure:

project/
├── Dockerfile
├── process_pdfs.py
├── requirements.txt
├── README.txt
├── input/
└── output/

📦 requirements.txt:

PyMuPDF==1.23.7

🐳 Dockerfile (Summary):

- Alpine-based, amd64 architecture
- No internet/network access required
- Converts all .pdf to .json
- No GPU, model size < 200MB

🧠 Script Behavior:

- Takes 2 arguments: input_dir and output_dir
- If not provided, defaults to /app/input and /app/output
