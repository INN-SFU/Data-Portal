import boto3
import json
import os


class ArbutusClient:
    def __init__(self):
        # Initialize S3 client with custom endpoint URL and signature version
        with open(os.getenv('ARBUTUS_CONFIG')) as f:
            config = json.load(f)
            s3 = boto3.client('s3',
                              endpoint_url='https://object-arbutus.cloud.computecanada.ca',
                              aws_access_key_id=config['aws_access_key_id'],
                              aws_secret_access_key=config['aws_secret_access_key'],
                              config=boto3.session.Config(signature_version='s3v4'))
        f.close()

        self.client = s3

    def list_buckets(self):
        return self.client.list_buckets()

    def list_objects(self, bucket_name):
        return self.client.list_objects(Bucket=bucket_name)

    def get_object(self, bucket_name, object_name):
        return self.client.get_object(Bucket=bucket_name, Key=object_name)

    def put_object(self, bucket_name, object_name, data):
        return self.client.put_object(Bucket=bucket_name, Key=object_name, Body=data)

    def delete_object(self, bucket_name, object_name):
        return self.client.delete_object(Bucket=bucket_name, Key=object_name)

    def create_bucket(self, bucket_name):
        return self.client.create_bucket(Bucket=bucket_name)

    def delete_bucket(self, bucket_name):
        return self.client.delete_bucket(Bucket=bucket_name)

    def generate_presigned_url(self, bucket_name: str, object_name: str, method: str, ttl: int) -> (
            str):
        return self.client.generate_presigned_url(ClientMethod=method,
                                                  Params={'Bucket': bucket_name,
                                                          'Key': object_name},
                                                  ExpiresIn=ttl)


if __name__ == "__main__":
    import dotenv

    dotenv.load_dotenv('/Users/pmahon/Research/INN/Data Portal/DAM/src/api/config/.env')
    def format_json(obj):
        return json.dumps(obj, indent=4, sort_keys=True, default=str)


    agent = ArbutusClient()

    upload_folder = "Users/pmahon/Desktop/test_folder"

    agent.put_folder(upload_folder, "def-rmcintos-dev-test", "test_folder")

