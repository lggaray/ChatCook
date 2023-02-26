# ChatCook: A Cooking Knowledge-Based Question Answering System For Personalized Nutrition of Chinese
## Personalized Nutrition Question Answering System
This is a repository for a personalized nutrition question answering system designed to provide accurate 
and relevant answers to a wide range of questions related to nutrition and cooking. 
The system is particularly tailored to the context of diverse Chinese cuisine and is designed to serve as 
both a kitchen assistant and a nutrition guide. The system incorporates a knowledge graph and a FAQ database
to provide more specific answers to user questions.

## Requirements
Please refer to the requirements file.
Some of the dependencies are:
* kglab
* rdflib
* numpy
* pandas
* pycnnum
* text2vec
* spacy (zh_core_web_lg)

## Usage (local)
To run the system, first download the code and the required dependencies. 
Then, run the `main.py`  script for running the system in console.

To run the system in localhost with a web interface, please run the `web_main.py` instead.

## Usage (web app)
To access the system running in our servers, please access to: https://dc1f-210-32-139-171.ngrok.io/

If the link is unaccessible, please contact us.

## Future Work
While the proposed system has shown promising results, there are still some limitations that need to be addressed to 
further improve its performance. These limitations include an incomplete FAQ database and a matching module
 that may not always return the best matching FAQ question due to the use of general domain embedding. 
Future work could focus on addressing these limitations and on expanding the system to incorporate more diverse
 cuisines and nutrition contexts.

## Contact
Lucas Garay: lucasgaray095@gmail.com
