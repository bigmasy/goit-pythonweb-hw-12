import cloudinary
import cloudinary.uploader

from fastapi import Depends
from src.conf.config import Settings, get_settings


class UploadFileService:
    """
    Service class for handling file uploads to Cloudinary.

    Initializes the Cloudinary configuration using credentials.

    :param cloud_name: Cloudinary cloud name.
    :type cloud_name: str
    :param api_key: Cloudinary API key.
    :type api_key: int
    :param api_secret: Cloudinary API secret.
    :type api_secret: str
    """
    def __init__(self, cloud_name, api_key, api_secret):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username) -> str:
        """
        Uploads a file stream to Cloudinary and generates a secure URL for the resource.

        The public ID is constructed using the 'RestApp/' prefix and the provided username,
        ensuring overwriting on subsequent uploads with the same username.
        The returned URL is resized to 250x250 with a 'fill' crop.

        :param file: The UploadFile object containing the file stream.
        :type file: :class:`fastapi.UploadFile`
        :param username: The username used to uniquely identify the uploaded file (public ID).
        :type username: str
        :return: The generated URL for the cropped and uploaded image.
        :rtype: str
        """
        public_id = f"RestApp/{username}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        src_url = cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )
        return src_url


async def get_uploader(settings: Settings = Depends(get_settings)) -> UploadFileService:
    """
    FastAPI dependency function to provide an instance of UploadFileService.

    It initializes the service with configuration settings retrieved via the `get_settings` dependency.

    :param settings: The application configuration settings.
    :type settings: :class:`src.conf.config.Settings`
    :return: An initialized UploadFileService instance.
    :rtype: :class:`UploadFileService`
    """
    return UploadFileService(
        cloud_name=settings.CLD_NAME,
        api_key=settings.CLD_API_KEY,
        api_secret=settings.CLD_API_SECRET,
    )