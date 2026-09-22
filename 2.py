import requests
import json

if __name__ == '__main__':
    url = "https://api.modelarts-maas.com/v1/embeddings"  # API地址
    api_key = "Ud260vor3oiXWn7OeEbHdJxqat60lfgheziuPlZ60R2R9XqYmLLAIo3jSa0AxXZO2f0uKL5ycj3QNqyxklw_XQ"  # 把MAAS_API_KEY替换成已获取的API Key

    # Send request.
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    texts = ["这是一只小猫", "这是一只小狗"]
    data = {
        "model": "bge-m3",  # model参数
        "input": texts,  # input类型可为string or string[]
        "encoding_format": "float"  # 取值范围："float","base64"
    }
    response = requests.post(url, headers=headers, data=json.dumps(data), verify=False)

    # Print result.
    print(response.status_code)
    print(response.text)
