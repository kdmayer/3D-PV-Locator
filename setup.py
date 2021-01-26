import os
import requests

def download_file_from_google_drive(id, destination):

    def get_confirm_token(response):
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value

        return None

    def save_response_content(response, destination):
        CHUNK_SIZE = 32768

        with open(destination, "wb") as f:
            for chunk in response.iter_content(CHUNK_SIZE):
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)

    URL = "https://docs.google.com/uc?export=download"

    session = requests.Session()

    response = session.get(URL, params = { 'id' : id }, stream = True)
    token = get_confirm_token(response)

    if token:
        params = { 'id' : id, 'confirm' : token }
        response = session.get(URL, params = params, stream = True)

    save_response_content(response, destination)

if __name__ == '__main__':

    file_id_dict = {'inceptionv3_weigths': '1WyHnoMyN8iixfQU8bdbJJn-kagLn798v', 'deeplabv3_weights': '1Mo--mdPlapfQsE0rXmpQXrYMbI_YCNzc'}

    for key, value in file_id_dict.items():

        if key == 'inceptionv3_weigths':

            destination = os.path.join(os.getcwd(), 'models', 'classification')

            if not os.path.exists(destination):

                os.makedirs(destination, exist_ok=True)

            print(f"Downloading the classification checkpoint to {destination} ... This might take a while")

            download_file_from_google_drive(value, destination + '/inceptionv3_weigths.tar')

            print("Classification checkpoint successfully downloaded")

        elif key == 'deeplabv3_weights':

            destination = os.path.join(os.getcwd(), 'models', 'segmentation')

            if not os.path.exists(destination):

                os.makedirs(destination, exist_ok=True)

            print(f"Downloading the segmentation checkpoint to {destination} ... This might take a while")

            download_file_from_google_drive(value, destination + '/deeplabv3_weights.tar')

            print("Segmentation checkpoint successfully downloaded")




