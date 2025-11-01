import streamlit as st
from streamlit_option_menu import option_menu
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from create_search_index import get_uploaded_filenames, delete_documents_by_filepath, prepare_documents, upload_documents_to_search
from chat_with_products import chat_with_doc
from utils import (
    get_youtube_transcript, extract_text_from_pdf, extract_text_from_docx,
    extract_text_from_txt, fetch_url_content, extract_audio_from_video,
    translate_audio_to_text
)


from azure.identity import EnvironmentCredential
credential = EnvironmentCredential()

# Streamlit page config
st.set_page_config(page_title="Chat Anything 🚀", page_icon="🧠", layout="wide")

# Sidebar
with st.sidebar:
    page = option_menu(
    menu_title="Chat Anything 🧠",
    options=["Chat", "Upload Files", "Manage Documents", "About"],
    icons=["chat-dots", "cloud-upload", "folder-minus", "info-circle"]
    )

# Initialize Azure AI Search client

# Session state to hold chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# Session state to hold chat history
if "chat_history2" not in st.session_state:
    st.session_state.chat_history2 = []
if "uploaded_text" not in st.session_state:
    st.session_state.uploaded_text = ""

# Upload page
if page == "Upload Files":
    st.header("📂 Upload and Process Media")

    media_type = st.selectbox("Select Media Type", ["PDF", "DOCX", "TXT", "YouTube", "Web URL", "Audio", "Video"])

    def process_and_upload(text, filename, category):
        """Chunks and uploads the text into Azure AI Search."""
        if text.startswith("Error:"):
            st.error(text)
        else:
            documents = prepare_documents(text, title=filename)
            upload_documents_to_search(index_name=os.environ["AISEARCH_INDEX_NAME"], documents=documents)
            st.success(f"✅ Your {category} was processed and indexed successfully. You can now chat with it!")

    if media_type == "PDF":
        uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
        if uploaded_file:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            text = extract_text_from_pdf(uploaded_file.name)
            process_and_upload(text, uploaded_file.name, "PDF")


    elif media_type == "DOCX":
        uploaded_file = st.file_uploader("Upload a DOCX file", type=["docx"])
        if uploaded_file:
            text = extract_text_from_docx(uploaded_file)
            process_and_upload(text, uploaded_file.name, "DOCX")

    elif media_type == "TXT":
        uploaded_file = st.file_uploader("Upload a TXT file", type=["txt"])
        if uploaded_file:
            text = extract_text_from_txt(uploaded_file)
            process_and_upload(text, uploaded_file.name, "TXT")

    elif media_type == "YouTube":
        youtube_url = st.text_input("Enter YouTube video URL")
        if youtube_url:
            text = get_youtube_transcript(youtube_url)
            process_and_upload(text, youtube_url, "YouTube")

    elif media_type == "Web URL":
        web_url = st.text_input("Enter Web page URL")
        if web_url:
            text = fetch_url_content(web_url)
            process_and_upload(text, web_url, "Web URL")

    elif media_type == "Audio":
        uploaded_file = st.file_uploader("Upload an Audio file", type=["mp3", "wav"])
        if uploaded_file:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            text = translate_audio_to_text(uploaded_file.name)
            process_and_upload(text, uploaded_file.name, "Audio")

    elif media_type == "Video":
        uploaded_file = st.file_uploader("Upload a Video file", type=["mp4", "mkv", "mov"])
        if uploaded_file:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            audio_path = extract_audio_from_video(uploaded_file.name)
            if audio_path and not audio_path.startswith("Error:"):
                text = translate_audio_to_text(audio_path)
                process_and_upload(text, uploaded_file.name, "Video")
            elif audio_path.startswith("Error:"):
                st.error(audio_path)

# Chat page
elif page == "Chat":
    st.title("💬 Chat with Your Uploaded Content")

    # Create two columns
    col1, col2 = st.columns([5, 1])  # Wider info, smaller clear button

    with col1:
        st.info("📂 Please upload and index a document first on the 'Upload Files' page.")
    with col2:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.chat_history2 = []
            st.rerun()

    # Display chat history
    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)

    # Chat input
    user_query = st.chat_input("Ask me anything about your uploaded media...")
    if user_query:
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.chat_history.append(("user", user_query))
        st.session_state.chat_history2.append({"role": "user", "content": user_query})

        # Perform search
        results = chat_with_doc(messages=st.session_state.chat_history2)
        
        if results:
            answer = results["message"]["content"]
        else:
            answer = "🤔 Sorry, I couldn't find any relevant information in the uploaded document."

        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state.chat_history.append(("assistant", answer))
        st.session_state.chat_history2.append({"role": "assistant", "content": answer})

# About page
elif page == "About":
    st.title("📘 About Chat Anything")
    st.markdown("""
    **Chat Anything** lets you upload any document and chat intelligently with its content!

    ### 🔧 How It Works
    - Upload files (PDF, DOCX, TXT)
    - We chunk & vectorize your content
    - You ask questions — we retrieve relevant answers instantly!

    ### 🌍 Built With
    - Python + Streamlit
    - Azure AI Search
    - Azure Embeddings

    ---
    Made with 💚 by Chemotronix!
    """)


# Manage Documents page
elif page == "Manage Documents":
    st.title("🗂️ Manage Uploaded Documents")

    filenames = get_uploaded_filenames()

    if filenames:
        selected_files = st.multiselect("Select one or more documents to delete:", filenames)

        if selected_files and st.button("❌ Delete Selected Documents"):
            with st.spinner("Deleting selected documents..."):
                for file in selected_files:
                    delete_documents_by_filepath(file)
            st.success(f"✅ Deleted {len(selected_files)} document(s) successfully!")
            st.rerun()
    else:
        st.info("📂 No documents found yet. Upload a file first.")



