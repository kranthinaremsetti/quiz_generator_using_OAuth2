import streamlit as st
import PyPDF2


def parse_topic_from_files(files):
    """
    Extract text content from uploaded PDF or TXT files.
    
    Args:
        files: List of uploaded files from Streamlit file_uploader
        
    Returns:
        str: Combined text content from all files
    """
    # Handle edge case of no files
    if not files:
        return ""
        
    all_topics = []

    for file in files:
        file.seek(0)  # Reset to start

        file_name = file.name
        text = ""

        if file_name.endswith(".txt"):
            try:
                file_content = file.read().decode("utf-8", errors="ignore")
                text = file_content.strip()
            except Exception as e:
                st.warning(f"Failed to read text file {file_name}: {e}")
            finally:
                file.seek(0)

        elif file_name.endswith(".pdf"):
            try:
                reader = PyPDF2.PdfReader(file)
                pdf_text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pdf_text += page_text + "\n"
                text = pdf_text.strip()
            except Exception as e:
                st.warning(f"Failed to read PDF file {file_name}: {e}")
            finally:
                file.seek(0)

        if text:
            # For multiple files, add prominent separation
            if len(files) > 1:
                section_header = f"\n{'='*50}\nSOURCE FILE {len(all_topics) + 1}: {file_name}\n{'='*50}\n"
                all_topics.append(f"{section_header}{text}")
            else:
                # Single file - just add the content cleanly
                all_topics.append(text)

    # If we have multiple files, try to balance the content
    if len(all_topics) > 1:
        # Reorganize content to ensure balanced representation
        balanced_content = []
        total_files = len(all_topics)
        
        # Add instruction for balanced processing
        instruction = f"\n{'*'*60}\nIMPORTANT: This content comes from {total_files} different files. Please generate questions that cover ALL {total_files} sources equally.\n{'*'*60}\n"
        balanced_content.append(instruction)
        
        # Add all content sections
        for i, topic in enumerate(all_topics, 1):
            balanced_content.append(f"\n[SECTION {i} OF {total_files}]\n{topic}")
        
        return "\n\n".join(balanced_content).strip()
    
    # Single file case
    return "\n\n".join(all_topics).strip()
