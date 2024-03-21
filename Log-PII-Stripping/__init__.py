import logging
import azure.functions as func
from azure.functions import EventHubEvent
from typing import List
import asyncio
import logging
from typing import List



async def main(events: List[EventHubEvent], outputDocument: func.Out[func.Document]):
    for event in events:
        output_binding_data = event.get_body().decode('utf-8')
        logging.info('Python EventHub trigger processed an event: %s',
                      output_binding_data)
        
        
        input_data: List[str] = []
        input_data.append(output_binding_data)

        output_binding_data = await analyze_pii_async(input_data)
        logging.info(f"PII stripped data: {output_binding_data}") 

        outputDocument.set(func.Document(output_binding_data))



async def analyze_pii_async(input_text: List[str]) -> None:
    # [START analyze_async]
    import os
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.textanalytics.aio import TextAnalyticsClient
    from azure.ai.textanalytics import (
        RecognizeEntitiesAction,
        RecognizeLinkedEntitiesAction,
        RecognizePiiEntitiesAction,
        ExtractKeyPhrasesAction,
        AnalyzeSentimentAction,
    )

    logging.info(f"input_text: {input_text}")

    # endpoint = os.environ["AZURE_LANGUAGE_ENDPOINT"]
    # key = os.environ["AZURE_LANGUAGE_KEY"]
    endpoint = "https://ai-sentry-cog-service.cognitiveservices.azure.com/"
    key = "8ae81ff4f7f844e6987b8bfb47e56822"

    text_analytics_client = TextAnalyticsClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )

    async with text_analytics_client:
        poller = await text_analytics_client.begin_analyze_actions(
            input_text,
            display_name="PII Analysis",
            actions=[
                RecognizePiiEntitiesAction()
            ]
        )

        pages = await poller.result()

        document_results = []
        async for page in pages:
            document_results.append(page)

    doc=""

    for doc, action_results in zip(input_text, document_results):
        for result in action_results:

            if result.kind == "PiiEntityRecognition":
                print("...Results of Recognize PII Entities action:")
                for pii_entity in result.entities:
                    logging.info(f"......Entity: {pii_entity.text}")
                    logging.info(f".........Category: {pii_entity.category}")
                    logging.info(f".........Confidence Score: {pii_entity.confidence_score}")
                    if pii_entity.confidence_score >= 0.8 and pii_entity.category != "DateTime":
                        logging.info(f"Removing PII entity: {pii_entity.text}, category: {pii_entity.category} from the logged payload")
                        doc = doc.replace(pii_entity.text, "*PII*")

            elif result.is_error is True:
                logging.info(f'PII-Processing: An error with code {result.error.code} and message {result.error.message}')
        
    if ": *PII*," in doc:
        doc = doc.replace(": *PII*,", ":\"*PII*\",")

    return doc