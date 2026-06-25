"""S3 storage utilities for optimization models.

This module provides helper functions to save and load trained optimization models
(e.g., Hill curve parameters, elasticity coefficients, forecasting models) to/from AWS S3.

Models are serialized using pickle and stored with metadata in the fitted_models table.

Usage
-----
```python
from worker.app.optimization.utils.s3_storage import upload_model, download_model

# Save trained model
model_data = {"alpha": 2.5, "k": 100.0, "s": 0.7}
s3_key = upload_model(model_data, "models/tenant_abc/hill_curve_2026-06-24.pkl")

# Load model later
loaded_model = download_model(s3_key)
```

Environment Variables
--------------------
- AWS_ACCESS_KEY_ID: AWS IAM access key
- AWS_SECRET_ACCESS_KEY: AWS IAM secret key
- S3_BUCKET_NAME: S3 bucket name (e.g., alpmark-optimization-models-production)
- S3_REGION: AWS region (e.g., ap-southeast-2)
"""

from __future__ import annotations

import logging
import os
import pickle
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# S3 configuration from environment
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "alpmark-optimization-models-production")
S3_REGION = os.getenv("S3_REGION", "ap-southeast-2")


def _get_s3_client():
    """Get configured S3 client.
    
    Returns
    -------
    boto3.client
        Configured S3 client using environment credentials.
    
    Raises
    ------
    ValueError
        If required AWS credentials are not set in environment.
    """
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not access_key or not secret_key:
        raise ValueError(
            "AWS credentials not found. Set AWS_ACCESS_KEY_ID and "
            "AWS_SECRET_ACCESS_KEY environment variables."
        )
    
    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=S3_REGION,
    )


def upload_model(model_obj: Any, s3_key: str) -> str:
    """Upload a trained model to S3.
    
    Serializes the model object using pickle and uploads to S3.
    
    Parameters
    ----------
    model_obj : Any
        The model object to upload (dict, numpy array, scikit-learn model, etc.).
        Must be pickle-serializable.
    s3_key : str
        S3 object key (path within bucket).
        Example: "models/tenant_abc123/hill_curve_2026-06-24.pkl"
    
    Returns
    -------
    str
        The S3 key where the model was uploaded.
    
    Raises
    ------
    pickle.PicklingError
        If the model object cannot be serialized.
    ClientError
        If S3 upload fails.
    
    Examples
    --------
    >>> model = {"alpha": 2.5, "k": 100.0, "s": 0.7}
    >>> s3_key = upload_model(model, "models/tenant_abc/hill_curve.pkl")
    >>> print(s3_key)
    models/tenant_abc/hill_curve.pkl
    """
    try:
        # Serialize model to bytes
        model_bytes = pickle.dumps(model_obj)
        
        # Upload to S3
        s3_client = _get_s3_client()
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=model_bytes,
            ContentType="application/octet-stream",
        )
        
        logger.info(
            f"Successfully uploaded model to s3://{S3_BUCKET_NAME}/{s3_key} "
            f"({len(model_bytes)} bytes)"
        )
        return s3_key
        
    except pickle.PicklingError as e:
        logger.error(f"Failed to serialize model: {e}")
        raise
    except ClientError as e:
        logger.error(f"Failed to upload model to S3: {e}")
        raise


def download_model(s3_key: str) -> Any:
    """Download a trained model from S3.
    
    Downloads the model from S3 and deserializes using pickle.
    
    Parameters
    ----------
    s3_key : str
        S3 object key (path within bucket).
        Example: "models/tenant_abc123/hill_curve_2026-06-24.pkl"
    
    Returns
    -------
    Any
        The deserialized model object.
    
    Raises
    ------
    ClientError
        If S3 download fails (e.g., key doesn't exist).
    pickle.UnpicklingError
        If the downloaded data cannot be deserialized.
    
    Examples
    --------
    >>> model = download_model("models/tenant_abc/hill_curve.pkl")
    >>> print(model["alpha"])
    2.5
    """
    try:
        # Download from S3
        s3_client = _get_s3_client()
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        model_bytes = response["Body"].read()
        
        # Deserialize model
        model_obj = pickle.loads(model_bytes)
        
        logger.info(
            f"Successfully downloaded model from s3://{S3_BUCKET_NAME}/{s3_key} "
            f"({len(model_bytes)} bytes)"
        )
        return model_obj
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            logger.error(f"Model not found at s3://{S3_BUCKET_NAME}/{s3_key}")
        else:
            logger.error(f"Failed to download model from S3: {e}")
        raise
    except pickle.UnpicklingError as e:
        logger.error(f"Failed to deserialize model: {e}")
        raise


def delete_model(s3_key: str) -> bool:
    """Delete a model from S3.
    
    Removes the model object from S3 storage.
    
    Parameters
    ----------
    s3_key : str
        S3 object key (path within bucket).
        Example: "models/tenant_abc123/hill_curve_2026-06-24.pkl"
    
    Returns
    -------
    bool
        True if deletion successful, False otherwise.
    
    Examples
    --------
    >>> success = delete_model("models/tenant_abc/hill_curve.pkl")
    >>> print(success)
    True
    """
    try:
        s3_client = _get_s3_client()
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        
        logger.info(f"Successfully deleted model at s3://{S3_BUCKET_NAME}/{s3_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Failed to delete model from S3: {e}")
        return False


def model_exists(s3_key: str) -> bool:
    """Check if a model exists in S3.
    
    Parameters
    ----------
    s3_key : str
        S3 object key (path within bucket).
    
    Returns
    -------
    bool
        True if model exists, False otherwise.
    
    Examples
    --------
    >>> if model_exists("models/tenant_abc/hill_curve.pkl"):
    ...     model = download_model("models/tenant_abc/hill_curve.pkl")
    """
    try:
        s3_client = _get_s3_client()
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        return True
    except ClientError:
        return False
