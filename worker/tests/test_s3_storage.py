"""Unit tests for S3 storage utilities.

Tests model upload, download, and deletion functionality using mocked S3 client.
"""

import os
import pickle
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from worker.app.optimization.utils.s3_storage import (
    delete_model,
    download_model,
    model_exists,
    upload_model,
)


@pytest.fixture
def mock_env_vars():
    """Mock AWS environment variables for testing."""
    with patch.dict(os.environ, {
        "AWS_ACCESS_KEY_ID": "test_access_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret_key",
        "S3_BUCKET_NAME": "alpmark-optimization-models-production",
        "S3_REGION": "ap-southeast-2",
    }):
        yield


@pytest.fixture
def mock_s3_client(mock_env_vars):
    """Mock boto3 S3 client for testing."""
    with patch("worker.app.optimization.utils.s3_storage.boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def sample_model():
    """Sample model object for testing."""
    return {
        "alpha": 2.5,
        "k": 100.0,
        "s": 0.7,
        "metadata": {
            "created_at": "2026-06-24",
            "accuracy": 0.87,
        },
    }


@pytest.fixture
def s3_key():
    """Sample S3 key for testing."""
    return "models/tenant_abc123/hill_curve_2026-06-24.pkl"


class TestUploadModel:
    """Tests for upload_model function."""
    
    def test_upload_model_success(self, mock_s3_client, sample_model, s3_key):
        """Test successful model upload to S3."""
        # Arrange
        mock_s3_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
        # Act
        result_key = upload_model(sample_model, s3_key)
        
        # Assert
        assert result_key == s3_key
        mock_s3_client.put_object.assert_called_once()
        
        # Verify the uploaded bytes can be unpickled back to original model
        call_args = mock_s3_client.put_object.call_args
        uploaded_bytes = call_args.kwargs["Body"]
        deserialized = pickle.loads(uploaded_bytes)
        assert deserialized == sample_model
    
    @pytest.mark.skip(reason="NumPy has compatibility issues with Python 3.14")
    def test_upload_model_with_numpy_array(self, mock_s3_client):
        """Test uploading a model containing numpy arrays."""
        import numpy as np
        
        # Arrange
        model = {
            "coefficients": np.array([1.5, 2.3, 0.8]),
            "intercept": 0.5,
        }
        s3_key = "models/test/numpy_model.pkl"
        mock_s3_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
        # Act
        result_key = upload_model(model, s3_key)
        
        # Assert
        assert result_key == s3_key
        call_args = mock_s3_client.put_object.call_args
        uploaded_bytes = call_args.kwargs["Body"]
        deserialized = pickle.loads(uploaded_bytes)
        assert np.array_equal(deserialized["coefficients"], model["coefficients"])
    
    def test_upload_model_s3_error(self, mock_s3_client, sample_model, s3_key):
        """Test upload failure due to S3 error."""
        # Arrange
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject"
        )
        
        # Act & Assert
        with pytest.raises(ClientError):
            upload_model(sample_model, s3_key)


class TestDownloadModel:
    """Tests for download_model function."""
    
    def test_download_model_success(self, mock_s3_client, sample_model, s3_key):
        """Test successful model download from S3."""
        # Arrange
        model_bytes = pickle.dumps(sample_model)
        mock_response = MagicMock()
        mock_response.__getitem__.return_value.read.return_value = model_bytes
        mock_s3_client.get_object.return_value = mock_response
        
        # Act
        downloaded_model = download_model(s3_key)
        
        # Assert
        assert downloaded_model == sample_model
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="alpmark-optimization-models-production",
            Key=s3_key
        )
    
    def test_download_model_not_found(self, mock_s3_client, s3_key):
        """Test download failure when model doesn't exist."""
        # Arrange
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}},
            "GetObject"
        )
        
        # Act & Assert
        with pytest.raises(ClientError):
            download_model(s3_key)
    
    def test_download_model_corrupted_data(self, mock_s3_client, s3_key):
        """Test download failure when pickle data is corrupted."""
        # Arrange
        corrupted_bytes = b"this is not valid pickle data"
        mock_response = MagicMock()
        mock_response.__getitem__.return_value.read.return_value = corrupted_bytes
        mock_s3_client.get_object.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(pickle.UnpicklingError):
            download_model(s3_key)


class TestDeleteModel:
    """Tests for delete_model function."""
    
    def test_delete_model_success(self, mock_s3_client, s3_key):
        """Test successful model deletion from S3."""
        # Arrange
        mock_s3_client.delete_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 204}}
        
        # Act
        result = delete_model(s3_key)
        
        # Assert
        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="alpmark-optimization-models-production",
            Key=s3_key
        )
    
    def test_delete_model_error(self, mock_s3_client, s3_key):
        """Test delete failure due to S3 error."""
        # Arrange
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "DeleteObject"
        )
        
        # Act
        result = delete_model(s3_key)
        
        # Assert
        assert result is False


class TestModelExists:
    """Tests for model_exists function."""
    
    def test_model_exists_true(self, mock_s3_client, s3_key):
        """Test checking existence of a model that exists."""
        # Arrange
        mock_s3_client.head_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
        # Act
        exists = model_exists(s3_key)
        
        # Assert
        assert exists is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="alpmark-optimization-models-production",
            Key=s3_key
        )
    
    def test_model_exists_false(self, mock_s3_client, s3_key):
        """Test checking existence of a model that doesn't exist."""
        # Arrange
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject"
        )
        
        # Act
        exists = model_exists(s3_key)
        
        # Assert
        assert exists is False


class TestIntegration:
    """Integration tests for S3 storage workflow."""
    
    def test_upload_download_cycle(self, mock_s3_client, sample_model, s3_key):
        """Test complete upload-download cycle."""
        # Arrange
        uploaded_bytes = None
        
        def capture_upload(*args, **kwargs):
            nonlocal uploaded_bytes
            uploaded_bytes = kwargs["Body"]
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        
        def mock_download(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.__getitem__.return_value.read.return_value = uploaded_bytes
            return mock_response
        
        mock_s3_client.put_object.side_effect = capture_upload
        mock_s3_client.get_object.side_effect = mock_download
        
        # Act
        upload_model(sample_model, s3_key)
        downloaded_model = download_model(s3_key)
        
        # Assert
        assert downloaded_model == sample_model
    
    def test_delete_nonexistent_model_is_safe(self, mock_s3_client, s3_key):
        """Test that deleting a non-existent model doesn't raise an error."""
        # Arrange
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}},
            "DeleteObject"
        )
        
        # Act
        result = delete_model(s3_key)
        
        # Assert
        assert result is False  # Should return False but not raise exception
