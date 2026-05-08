import streamlit as st
import os
import io
import uuid
import time
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import azure.cognitiveservices.speech as speechsdk

# ----------------------------- #
# CONFIGURATION - Azure Services  #
# ----------------------------- #

# Azure Computer Vision Credentials (from existing notebook cells)
CV_ENDPOINT = "https://cv97898657.cognitiveservices.azure.com/"
CV_API_KEY = "3rjI2tJgEjvUS9ve9DnwGTdgu0JW5B5i0u2mE8QpRzgaCPh4l1AwJQQJ99CEACYeBjFXJ3w3AAAFACOG0FxE"

# Azure Speech Service Credentials (from existing notebook cells)
SPEECH_KEY = "2LNcNfQUrK6f0jj3eZ1ssHm1qALaeiXmn1foajdEdGGo9bxH06i5JQQJ99CEACYeBjFXJ3w3AAAYACOGrjDr"
SPEECH_REGION = "eastus"

# ---------------------------------------- #
# Text-to-Speech Function (adapted for Streamlit) #
# ---------------------------------------- #
def text_to_speech(text_to_synthesize, output_filename=None):
    if not text_to_synthesize.strip():
        st.warning("No text provided for speech synthesis.")
        return None

    if output_filename is None:
        # Generate a unique temporary filename for the audio
        output_filename = f"audio_{uuid.uuid4()}.wav"

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=SPEECH_KEY,
            region=SPEECH_REGION
        )
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        audio_config = speechsdk.audio.AudioConfig(filename=output_filename)

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        # Convert text to speech
        result = synthesizer.speak_text_async(text_to_synthesize).get()

        # Check result
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return output_filename
        else:
            st.error(f"Speech synthesis failed.")
            st.error(f"Reason: {result.reason}")
            return None
    except Exception as e:
        st.error(f"An error occurred during speech synthesis: {e}")
        return None

# ----------------------------- #
# Streamlit Application Layout  #
# ----------------------------- #
def main():
    st.set_page_config(page_title="Image OCR & Text-to-Speech", layout="centered")
    st.title("📄 Image OCR & 🗣️ Text-to-Speech")

    st.markdown(
        """
        Upload an image containing text, and this app will perform Optical Character Recognition (OCR)
        to extract the text. Then, it will convert the extracted text into spoken audio.
        """
    )

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png", "bmp", "tiff"])

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        st.write("")
        st.info("Performing OCR and Text-to-Speech. Please wait...")

        temp_image_path = None
        audio_file_path = None

        try:
            # Create a temporary file for the uploaded image to be read by Computer Vision client
            # Use a unique name to avoid conflicts if multiple uploads happen
            file_extension = uploaded_file.name.split('.')[-1]
            temp_image_path = f"temp_uploaded_image_{uuid.uuid4()}.{file_extension}"
            with open(temp_image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Initialize Computer Vision client
            computervision_client = ComputerVisionClient(
                CV_ENDPOINT,
                CognitiveServicesCredentials(CV_API_KEY)
            )

            # Perform OCR (Read API)
            with open(temp_image_path, "rb") as image_stream:
                read_response = computervision_client.read_in_stream(image_stream, raw=True)

            # Get Operation ID from the headers
            operation_id = read_response.headers["Operation-Location"].split("/")[-1]

            # Wait for OCR result
            while True:
                read_result = computervision_client.get_read_result(operation_id)
                if read_result.status not in ["notStarted", "running"]:
                    break
                time.sleep(1)

            combined_text = ""
            if read_result.status == "succeeded":
                st.subheader("Extracted Text (OCR Result):")
                for page in read_result.analyze_result.read_results:
                    for line in page.lines:
                        combined_text += line.text + "\n"
                st.text_area("OCR Output", combined_text.strip(), height=200)
            else:
                st.error(f"OCR failed with status: {read_result.status}")

            # Convert extracted text to speech if available
            if combined_text.strip():
                st.subheader("Text-to-Speech Audio:")
                audio_file_path = text_to_speech(combined_text.strip())
                if audio_file_path and os.path.exists(audio_file_path):
                    # Read audio file bytes for Streamlit audio player
                    with open(audio_file_path, "rb") as audio_file:
                        audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/wav")
                elif not audio_file_path:
                    st.warning("Could not generate audio.")
            else:
                st.warning("No text extracted, so no audio will be generated.")

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
        finally:
            # Clean up temporary files
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if audio_file_path and os.path.exists(audio_file_path):
                os.remove(audio_file_path)

# Run the Streamlit app
if __name__ == "__main__":
    main()
