# /// script
# requires-python = ">=3.11"
# dependencies = [
# "httpx",
# "pandas",
# "matplotlib",
# "requests",
# "seaborn",
# "charset_normalizer",
# "chardet",
# ]
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)

# Verify Environment Variable
if "AIPROXY_TOKEN" not in os.environ:
    logging.error("AIPROXY_TOKEN environment variable is not set.")
    sys.exit(1)

AIPROXY_TOKEN = os.environ["AIPROXY_TOKEN"]

# Function to load dataset
def load_dataset(file_path: str) -> pd.DataFrame:
    try:
        data = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        logging.info("UTF-8 decoding failed. Trying ISO-8859-1...")
        try:
            data = pd.read_csv(file_path, encoding='ISO-8859-1')
        except Exception as e:
            logging.error(f"Error loading dataset: {e}")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading dataset: {e}")
        sys.exit(1)
    return data

# Function to analyze the dataset
def analyze_dataset(df: pd.DataFrame) -> dict:
    return {
        "columns": list(df.columns),
        "data_types": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "summary_stats": df.describe(include="all").to_dict()
    }

# Function to visualize data
def visualize_data(df: pd.DataFrame, output_folder: str) -> list:
    chart_paths = []
    numeric_df = df.select_dtypes(include=['number'])

    if not numeric_df.empty:
        plt.figure(figsize=(10, 8))
        sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm")
        plt.title("Correlation Heatmap")
        heatmap_path = os.path.join(output_folder, "heatmap.png")
        plt.savefig(heatmap_path, dpi=150)
        plt.close()
        chart_paths.append(heatmap_path)

    plt.figure(figsize=(10, 6))
    sns.heatmap(df.isnull(), cbar=False, cmap='viridis')
    plt.title("Missing Values Heatmap")
    missing_values_path = os.path.join(output_folder, "missing_values.png")
    plt.savefig(missing_values_path, dpi=150)
    plt.close()
    chart_paths.append(missing_values_path)

    return chart_paths

# Function to send request to AI Proxy (GPT-4o-Mini)
def generate_narration(prompt: str, retries=3, delay=5) -> str:
    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {AIPROXY_TOKEN}"}
    data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}

    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            logging.error(f"Error generating narration: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
    logging.error("Max retries reached. Exiting.")
    sys.exit(1)

# Create output folder if it does not exist
def create_output_folder(file_path: str) -> str:
    folder_name = os.path.splitext(os.path.basename(file_path))[0]  # Get filename without extension
    output_folder = os.path.join(os.path.dirname(file_path), folder_name)  # Create path for the folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    return output_folder

# Main function
def main(file_path: str):
    output_folder = create_output_folder(file_path)  # Automatically create a folder with the filename
    df = load_dataset(file_path)

    if df is None or df.empty:
        logging.error(f"Error: Dataset at {file_path} could not be loaded or is empty.")
        sys.exit(1)

    summary = analyze_dataset(df)
    story = generate_narration("Provide a summary of the dataset based on the columns, missing values, and summary statistics.")
    
    chart_paths = visualize_data(df, output_folder)
    
    readme_path = os.path.join(output_folder, "README.md")
    with open(readme_path, "w") as f:
        f.write(f"# Automated Analysis Report\n\n")
        f.write(f"## Dataset Summary\n\n")
        f.write(f"### Columns\n{summary['columns']}\n\n")
        f.write(f"### Data Types\n{summary['data_types']}\n\n")
        f.write(f"### Missing Values\n{summary['missing_values']}\n\n")
        f.write(f"### Summary Statistics\n{summary['summary_stats']}\n\n")
        f.write(f"## Story\n{story}\n\n")
        f.write("## Visualizations\n")
        for chart in chart_paths:
            f.write(f"![Visualization]({chart})\n")

    logging.info(f"Analysis completed. Results saved in {output_folder}/README.md and visualizations.")

if __name__ == "__main__":
    file_path = sys.argv[1]  # Get the file path from the command-line argument
    main(file_path)
