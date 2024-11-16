from flask import Flask, request, Response
from lxml import etree
import os

app = Flask(__name__)

def leer_cuentas():
    cuentas = {}
    if not os.path.exists('cuentas'):
        os.makedirs('cuentas')
    
    # Iterar sobre todos los archivos en la carpeta 'cuentas'
    for archivo in os.listdir('cuentas'):
        if archivo.endswith('.xml'):  # buca los archivos con la extension .xml
            archivo_path = os.path.abspath(os.path.join('cuentas', archivo))
            if os.path.exists(archivo_path):
                try:
                    # Intenta parsear el archivo XML
                    tree = etree.parse(archivo_path)
                    root = tree.getroot()
                    
                    # Obtenemos el numero de tarjeta
                    numero = root.find('tarjeta').text
                    # Almacenamos la informacion de la cuenta en el diccionario
                    cuentas[numero] = {
                        'tarjeta': root.find('tarjeta').text,
                        'fechaVencimiento': root.find('fechaVencimiento').text,
                        'nip': root.find('nip').text,
                        'saldo': float(root.find('saldo').text),
                        'limite': float(root.find('limite').text),
                        'intentos': int(root.find('intentos').text),
                        'estadoTarjeta': root.find('estadoTarjeta').text
                    }
                except etree.XMLSyntaxError as e:
                    print(f"Error de sintaxis XML en el archivo {archivo}: {e}")
                except OSError as e:
                    print(f"Error al leer el archivo {archivo}: {e}")
                except Exception as e:
                    print(f"Error inesperado al procesar el archivo {archivo}: {e}")
            else:
                print(f"El archivo {archivo_path} no existe.")
    return cuentas


@app.route("/atm", methods=["POST"])
def atm():
    cuentas = leer_cuentas()
    xml_data = request.data
    root = etree.fromstring(xml_data)

    # Verificar que todos los elementos requeridos existan en el XML recibido
    tarjeta_elem = root.find('tarjeta')
    nip_elem = root.find('nip')
    cantidad_elem = root.find('cantidad')

    if tarjeta_elem is None or nip_elem is None or cantidad_elem is None:
        return Response("<response>Error: XML malformado o elementos faltantes</response>", content_type="application/xml")

    numero = tarjeta_elem.text
    nip = nip_elem.text
    cantidad = float(cantidad_elem.text)
    
    if numero not in cuentas:
        return Response("<response>Error: Tarjeta no registrada</response>", content_type="application/xml")
    
    cuenta = cuentas[numero]

    # Verificamos si la tarjeta esta bloqueada por intentos fallidos
    if cuenta['intentos'] == 0:
        return Response("<response>Error: Tarjeta bloqueada por intentos fallidos</response>", content_type="application/xml")
    
    if cuenta['estadoTarjeta'] != "verificada":
        return Response("<response>Error: Tarjeta no verificada</response>", content_type="application/xml")
    
    if cuenta['fechaVencimiento'] == "expirada":
        return Response("<response>Error: Tarjeta expirada</response>", content_type="application/xml")
    
    if cuenta['nip'] != nip:
        cuenta['intentos'] -= 1  # Decrementamos los intendos
        if cuenta['intentos'] == 0:
            # Si los intentos llegan a cero, bloqueamos la tarjeta
            cuenta['estadoTarjeta'] = "bloqueada"
            # Actualizamos el archivo XML con los nuevos intentos y estado
            archivo = os.path.abspath(os.path.join('cuentas', f'{numero}.xml'))
            try:
                tree = etree.parse(archivo)
                root = tree.getroot()
                root.find('intentos').text = str(cuenta['intentos'])
                root.find('estadoTarjeta').text = "bloqueada"
                tree.write(archivo)
            except etree.XMLSyntaxError as e:
                return Response(f"<response>Error al actualizar el archivo XML: {e}</response>", content_type="application/xml")
            
            return Response("<response>Error: Tarjeta bloqueada</response>", content_type="application/xml")
        
        # Actualizamos los intentos restantes en el archivo XML
        archivo = os.path.abspath(os.path.join('cuentas', f'{numero}.xml'))
        try:
            tree = etree.parse(archivo)
            root = tree.getroot()
            root.find('intentos').text = str(cuenta['intentos'])
            tree.write(archivo)
        except etree.XMLSyntaxError as e:
            return Response(f"<response>Error al actualizar el archivo XML: {e}</response>", content_type="application/xml")
        
        return Response(f"<response>Error: NIP incorrecto. Intentos restantes: {cuenta['intentos']}</response>", content_type="application/xml")
    
    if cuenta['saldo'] < cantidad:
        return Response("<response>Error: Saldo insuficiente</response>", content_type="application/xml")
    
    if cantidad > cuenta['limite']:
        return Response("<response>Error: Limite excedido</response>", content_type="application/xml")
    
    cuenta['saldo'] -= cantidad
    
    # Actualizamos el saldo y los intentos en el archivo XML
    archivo = os.path.abspath(os.path.join('cuentas', f'{numero}.xml'))
    
    if not os.path.exists(archivo):
        return Response(f"<response>Error: El archivo {archivo} no se encuentra en la ruta especificada</response>", content_type="application/xml")
    
    try:
        tree = etree.parse(archivo)
        root = tree.getroot()
        root.find('saldo').text = str(cuenta['saldo'])
        root.find('intentos').text = str(cuenta['intentos'])
        tree.write(archivo)
    except etree.XMLSyntaxError as e:
        return Response(f"<response>Error al actualizar el archivo XML: {e}</response>", content_type="application/xml")
    
    return Response("<response>Retiro exitoso</response>", content_type="application/xml")

if __name__ == "__main__":
    app.run(debug=True)
