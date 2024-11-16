import requests

url = "http://localhost:5000/atm"

# Ejemplo de solicitud XML con la estructura correcta
xml_request = """
<Cuenta>
    <tarjeta>1111-1111-1111-1111</tarjeta>
    <nip>13</nip>
    <cantidad>1000</cantidad>
</Cuenta>
"""

headers = {"Content-Type": "text/xml"}

response = requests.post(url, data=xml_request, headers=headers)
print(response.text)
