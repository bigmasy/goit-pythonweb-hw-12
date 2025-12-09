from unittest.mock import Mock, patch

from src.services.upload_file import UploadFileService

@patch("cloudinary.config")
def test_upload_file_constructor(mocked_cloudinary_config):
    """Test the UploadFileService class constructor."""
    uploader = UploadFileService(
        cloud_name="dev-test",
        api_key=123456,
        api_secret="test",
    )

    assert uploader.cloud_name == "dev-test"
    assert uploader.api_key == 123456
    assert uploader.api_secret == "test"

    assert mocked_cloudinary_config.call_count == 1
    kwargs = mocked_cloudinary_config.call_args.kwargs
    assert kwargs.get("cloud_name") == "dev-test"
    assert kwargs.get("api_key") == 123456
    assert kwargs.get("api_secret") == "test"
    assert kwargs.get("secure") is True


@patch("cloudinary.CloudinaryImage.build_url")
@patch("cloudinary.uploader.upload")
@patch("cloudinary.config")
def test_upload_file(mocked_config, mock_upload, mock_build_url):
    """Test the upload_file staticmethod for the UploadFileService class."""
    uploader = UploadFileService(
        cloud_name="test",
        api_key=123456,
        api_secret="test",
    )
    assert mocked_config.call_count == 1

    mock_upload_file = Mock(name="test_me_pls", file=77)

    mock_upload.return_value = {"version": 5}
    mock_build_url.return_value = "https://example.com/image.jpg"

    result = uploader.upload_file(
        file=mock_upload_file,
        username='test',
    )
    assert result == "https://example.com/image.jpg"
    assert mock_upload.call_count == 1
    assert mock_build_url.call_count == 1

    args = mock_upload.call_args.args
    assert args == (mock_upload_file.file,)
    kwargs = mock_upload.call_args.kwargs
    assert kwargs.get("public_id") == f'RestApp/test'
    assert kwargs.get("overwrite") is True

    kwargs = mock_build_url.call_args.kwargs
    assert kwargs.get("width") == 250
    assert kwargs.get("height") == 250
    assert kwargs.get("crop") == "fill"
    assert kwargs.get("version") == mock_upload.return_value.get("version")
