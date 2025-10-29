import requests

url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29"

body = {
	"input": """Write a short story about anything""",
	"parameters": {
		"decoding_method": "greedy",
		"max_new_tokens": 200,
		"min_new_tokens": 0,
		"repetition_penalty": 1
	},
	"model_id": "meta-llama/llama-3-3-70b-instruct",
	"project_id": "d9206445-c488-4f02-9441-aee55859d443"
}

headers = {
	"Accept": "application/json",
	"Content-Type": "application/json",
	"Authorization": "Bearer u961rTHPTdFB9rP2cbfgn7IA3Fn-FuuifswSfuAq4AkH"
}

response = requests.post(
	url,
	headers=headers,
	json=body
)

if response.status_code != 200:
	raise Exception("Non-200 response: " + str(response.text))

data = response.json()
print(data)