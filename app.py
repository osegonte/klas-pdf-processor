import streamlit as st
import json
from pathlib import Path
import tempfile
from main import create_boxes

st.set_page_config(page_title="PDF Box Creator", page_icon="📦", layout="wide")

st.title("PDF Box Creator")
st.caption("Team Sego format with PDF chunks")

uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])

if uploaded_file:
    material_id = st.text_input("Material ID (optional)", placeholder="Leave empty to auto-generate")
    
    if st.button("Process PDF", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        with st.spinner("Processing..."):
            try:
                boxes_json, chunks_dir = create_boxes(
                    tmp_path,
                    material_id=material_id if material_id else None
                )
                
                with open(boxes_json) as f:
                    data = json.load(f)
                
                st.success("Processing complete!")
                
                # Stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Pages", data['metadata']['total_pages'])
                with col2:
                    st.metric("Boxes", len(data['boxes']))
                with col3:
                    exercises = sum(1 for b in data['boxes'] if b['is_exercise'])
                    st.metric("Exercises", exercises)
                
                st.divider()
                
                # Show boxes
                st.subheader("Boxes")
                
                for box in data['boxes']:
                    with st.expander(f"{box['box_type'].upper()}: {box['title']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Pages:** {box['page_start']}-{box['page_end']}")
                            st.write(f"**Type:** {box['box_type']}")
                            st.write(f"**Words:** {box['metadata']['word_count']:,}")
                            st.write(f"**Reading time:** {box['metadata']['estimated_reading_minutes']} min")
                        
                        with col2:
                            st.write(f"**Has images:** {'Yes' if box['metadata']['has_images'] else 'No'}")
                            st.write(f"**Has code:** {'Yes' if box['metadata']['has_code'] else 'No'}")
                            st.write(f"**Chunk size:** {box['chunk_size_mb']} MB")
                            
                            # Download button for PDF chunk
                            chunk_path = Path(boxes_json).parent / box['pdf_chunk_file']
                            if chunk_path.exists():
                                with open(chunk_path, 'rb') as f:
                                    st.download_button(
                                        "Download PDF Chunk",
                                        f.read(),
                                        file_name=f"{box['temp_id']}.pdf",
                                        mime="application/pdf"
                                    )
                        
                        st.text_area(
                            "Preview",
                            box['content_preview'],
                            height=100,
                            key=f"preview_{box['temp_id']}"
                        )
                        
                        if box['is_exercise']:
                            st.info(f"Exercise Type: {box['exercise_type']}")
                
                # Download full output
                st.divider()
                with open(boxes_json) as f:
                    st.download_button(
                        "Download boxes.json (Team Sego format)",
                        f.read(),
                        file_name="boxes.json",
                        mime="application/json"
                    )
                
            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)
        
        Path(tmp_path).unlink(missing_ok=True)

else:
    st.info("Upload a PDF to begin")
    
    with st.expander("Output Format"):
        st.markdown("""
        **Team Sego Compatible Output:**
        - `boxes.json` - API-ready format
        - `chunks/` - Individual PDF files for each box
        
        **Each box includes:**
        - Content preview (200-500 chars)
        - Actual PDF chunk (preserves images, formatting)
        - Metadata (word count, images, code detection)
        - Exercise detection
        """)
