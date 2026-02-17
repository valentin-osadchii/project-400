import os
import requests
import json
from bs4 import BeautifulSoup
import markdownify
import re
from bs4.element import Comment
import argparse  # Added argparse for command-line argument parsing


# CONFIG
CONFLUENCE_URL = "https://confluence.sberbank.ru/" # Cloud
# CONFLUENCE_URL = "https://your-confluence-server" # Server/DC
TOKEN = "###" # Personal Access Token

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Confluence Extractor")
parser.add_argument("--page-id", required=True, help="Page ID to extract")
args = parser.parse_args()
PAGE_ID = args.page_id  # Dynamically assign PAGE_ID from command-line argument

SAVE_PATH = "./exported-pages/" + PAGE_ID + "/"
os.makedirs(SAVE_PATH, exist_ok=True)

# GET PAGE CONTENT + ATTACHMENTS
headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"}
url = f"{CONFLUENCE_URL}/rest/api/content/{PAGE_ID}?expand=body.storage,version,children.attachment"
response = requests.get(url, headers=headers, verify='./conf-cert.pem')
page_data = response.json()

# EXTRACT:
text_content = page_data["body"]["storage"]["value"] # Raw storage format (XHTML)
attachments = page_data["children"]["attachment"]["results"]

# SAVE HTML FILE
html_filename = f"{SAVE_PATH}{PAGE_ID}.html"
with open(html_filename, "w") as f:
    f.write(text_content)



# Преобразуем HTML в Markdown
markdown_content = markdownify.markdownify(text_content, heading_style='ATX')



# СОХРАНЕНИЕ MARKDOWN ФАЙЛА
md_filename = f"{SAVE_PATH}{PAGE_ID}.md"
with open(md_filename, "w") as f:
    f.write(markdown_content)

# DOWNLOAD AND SAVE ATTACHMENTS
for attachment in attachments:
    print(attachment, flush=True, end='\n')
    download_url = f"{CONFLUENCE_URL}{attachment['_links']['download']}"
    attachment_response = requests.get(download_url, headers=headers, verify='./conf-cert.pem')

    # Check if the attachment is a draw.io diagram
    media_type = attachment.get('metadata', {}).get('mediaType', '')
    if media_type != 'application/vnd.jgraph.mxfile':
        continue

    # Save the file with the original filename
    attachment_path = f"{SAVE_PATH}{attachment['title']}" + ".drawio"

    # Write the file
    with open(attachment_path, "wb") as f:
        f.write(attachment_response.content)


from markdownify import MarkdownConverter
from bs4 import BeautifulSoup

import re
from markdownify import MarkdownConverter
from bs4 import BeautifulSoup
from bs4.element import Comment

import sys
sys.setrecursionlimit(1000)

# Создаем собственный конвертер Markdown
class CustomMarkdownConverter(MarkdownConverter):
    def convert_ac_structured_macro(self, element, *args, parent_tags=None, **kwargs):
        macro_name = element.get('ac:name')
        
        # Обрабатываем макрос кода
        if macro_name == 'code':
            language_param = element.find('ac:parameter', {'ac:name': 'language'})
            language = language_param.text if language_param else ''
            
            # Прямая обработка CDATA
            body_element = element.find('ac:plain-text-body')
            if body_element and isinstance(body_element.contents[0], Comment):
                # Извлекаем чистое содержимое CDATA
                raw_cdata = body_element.contents[0].string
                # Удаляем лишние символы
                cleaned_code = raw_cdata.replace('[CDATA[', '').replace(']]', '').strip()
            else:
                cleaned_code = body_element.text if body_element else ''
            
            # Формируем Markdown-код
            return f"\```{language}\n{cleaned_code}\```\n"
            
            

        
        # Пропускаем элементы, которые могут вызывать рекурсию
        if element.name in ['ac:structured-macro']:
            return ""
        
        # Возвращаем обработку родителю, если макрос неизвестен
        return self.process_tag(element, parent_tags=parent_tags)

# Основная логика
def process_html_to_markdown(text_content):
    # Чистим HTML от стилей
    soup = BeautifulSoup(text_content, features="lxml")
    for tag in soup.find_all(True):
        tag.attrs.pop('style', None)
    
    # Регистрация нового обработчика макросов
    converter = CustomMarkdownConverter()
    
    # Преобразуем HTML в Markdown
    markdown_content = converter.convert(str(soup))
    
    return markdown_content



markdown_result_wth_code = process_html_to_markdown(text_content)


# СОХРАНЕНИЕ MARKDOWN ФАЙЛА
md_filename_2 = f"{SAVE_PATH}{PAGE_ID}_with_code.md"
with open(md_filename_2, "w") as f:
    f.write(markdown_result_wth_code)
