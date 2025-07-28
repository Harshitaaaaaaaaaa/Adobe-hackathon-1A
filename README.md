# PDF Heading and Outline Extractor

This Python script intelligently extracts a structured table of contents (outline) from PDF files. It uses a combination of advanced heuristics—including font styles, page layout, vertical spacing, and a weighted scoring system—to identify headings and their hierarchical levels (H1, H2, H3).

The primary goal is to convert a visually structured PDF into a machine-readable JSON format, providing a clean and accurate outline of the document's contents.

## ✨ Features

* **Intelligent Heading Detection:** Uses a scoring system based on font size, weight, and layout to accurately identify headings.
* **Hierarchical Outline Generation:** Automatically determines heading levels (H1, H2, H3) to create a nested, logical structure.
* **Multi-Language Support:** Easily configurable for different languages. Comes with built-in patterns for English and Chinese, and can be extended via the `languages.json` file.
* **Embedded ToC Priority:** Automatically uses the PDF's built-in table of contents if available for maximum accuracy.
* **Header/Footer Filtering:** Detects and ignores repetitive text in page headers and footers to avoid including them in the outline.
* **Dockerized & Secure:** Comes with a multi-stage `Dockerfile` for a small, fast, and secure production image.

---

## 🛠️ Setup

### Prerequisites

* Python 3.9+
* Docker (for containerized execution)

### Project Structure

project/
├── Dockerfile
├── .dockerignore
├── languages.json
├── process_pdfs.py
├── requirements.txt
├── README.md
└── sample_datasets/
├── pdfs/
│   └── your_document.pdf
└── outputs/


### Installation

1.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Language Configuration (`languages.json`)**
    This file contains regular expressions to detect numbered headings for different languages. You can easily add new languages.
    ```json
    {
      "en": {
        "numbered_heading_regex": "^(\\d[\\d.]*|[IVXLCDM]+\\.|[A-Z]\\.)\\s+"
      },
      "zh": {
        "numbered_heading_regex": "^([一二三四五六七八九十]+、|（[一二三四五六七八九十]）|\\d[\\d.]*)\\s+"
      }
    }
    ```

---

## ▶️ Usage

### Local Execution

To run the script directly on your machine:

```bash
python process_pdfs.py ./path/to/your/pdfs ./path/to/your/outputs --lang en
--lang en: Use the English language configuration.

--lang zh: Use the Chinese language configuration.

Docker Execution
This is the recommended method for a consistent and isolated environment.

Build the Docker Image:
From the project's root directory, run:

Bash

docker build -t pdf-extractor .
Run the Container:
This command mounts your local input and output directories into the container and processes the files.

Bash

docker run --rm \
  -v ./sample_datasets/pdfs:/app/input \
  -v ./sample_datasets/outputs:/app/output \
  pdf-extractor sample_datasets/pdfs sample_datasets/outputs --lang en
--rm: Automatically removes the container after it finishes.

-v: Mounts a local directory into a container directory.

pdf-extractor: The name of the image you just built.

./input ./output --lang en: Arguments passed to the Python script inside the container.