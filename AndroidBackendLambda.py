from __future__ import print_function

import boto3
import json
import base64
print('Loading function')
dynamo = boto3.client('dynamodb')
import random
import time
print('Loading function')

dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')


# --------------- Helper Functions ------------------

def transcribe_audio(file_name):
    transcribe = boto3.client('transcribe')
    # job_name = "job name"
    job_uri = "https://s3.amazonaws.com/myrecognition/audio/"+file_name
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='wav',
        LanguageCode='en-US'
    )
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        print("Not ready yet...")
    return status['result']['transcript']

def index_faces(bucket, key):

    response = rekognition.index_faces(
        Image={"S3Object":
            {"Bucket": bucket,
            "Name": key}},
            CollectionId="family_collection")
    return response
    
def update_index(tableName,faceId, fullName):
    response = dynamodb.put_item(
        TableName=tableName,
        Item={
            'RekognitionId': {'S': faceId},
            'viFullName': {'S': str(int(time.time()))}
            }
        ) 


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


import base64
import re
s3 = boto3.resource('s3')

    
def lambda_handler(event, context):
    '''Demonstrates a simple HTTP endpoint using API Gateway. You have full
    access to the request and response payload, including headers and
    status code.

    To scan a DynamoDB table, make a GET request with the TableName as a
    query string parameter. To put, update, or delete an item, make a POST,
    PUT, or DELETE request respectively, passing in the payload to the
    DynamoDB API as a JSON body.
    '''
    #print("Received event: " + json.dumps(event, indent=2))
    
    print("EVENT "+str(event))
    action = event.get("task","NO").lower()
    file_binary = event.get("filename","")
    if action =="save":
        base_  =str(int(time.time()))
        file_name = base_ +".jpg"
        object = s3.Object('myrecognition','index/'+ file_name)
        inp = base64.decodestring(file_binary)
        ret = object.put(Body=inp,Metadata={'FullName':base_})
        return {"status":"OK"}
    elif action == "saveaudio":
        base_  =str("configaudio")
        file_name = base_ +".wav"
        object = s3.Object('myrecognition','audio/'+ file_name)
        inp = base64.decodestring(file_binary)
        ret = object.put(Body=inp,Metadata={'FullName':base_})
        pass_phrase = transcribe_audio(file_name)
        # save_passphrase_in_dynamo('audio',pass_phrase)
        return {"status":"OK"}
    elif action == "testaudio":
        base_  =str(int(time.time()))
        file_name = base_ +".wav"
        object = s3.Object('myrecognition','audio/'+ file_name)
        inp = base64.decodestring(file_binary)
        ret = object.put(Body=inp,Metadata={'FullName':base_})
        received_phrase = transcribe_audio(file_name)
        actual_phrase = transcribe_audio("configaudio.wav")
        if received_phrase == actual_phrase:
            return {"status":"OK"}
        else:
            return {"status": "NOK"}
    else:
        if file_binary != "":
            # image_binary += "=" * ((4 - len(image_binary) % 4) % 4)
            inp = base64.decodestring(file_binary)
            # inp = decode_base64(image_binary)
            response = rekognition.search_faces_by_image(
            CollectionId='family_collection',
            Image={'Bytes':inp}
            )
            face = None
            print(response)
            for match in response['FaceMatches']:
                print (match['Face']['FaceId'],match['Face']['Confidence'])
            
                face = dynamodb.get_item(
                    TableName='family_collection',
                    Key={'RekognitionId': {'S': match['Face']['FaceId']}}
                    )
            if face:
                return {"status":"OK"}
            else:
                return {"status":"NOK"}
    return {"status":"NOK"}
