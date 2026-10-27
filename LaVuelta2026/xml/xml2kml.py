# xml2kml.py
# -*- coding: utf-8 -*-
""""
Crea archivos KML con puntos y líneas

@version 1.1 19/Octubre/2024
@author: Juan Manuel Cueva Lovelle. Universidad de Oviedo
"""

import xml.etree.ElementTree as ET


class Kml(object):
    """
    Lee un XML de etapa y genera un archivo KML con puntos y una línea.
    """

    NS_XML = {'u': 'http://www.uniovi.es'}
    NS_KML = 'http://www.opengis.net/kml/2.2'

    # Colores KML en formato aabbggrr
    ROJO = 'ff0000ff'
    VERDE = 'ff00ff00'
    AZUL = 'ffff0000'
    AMARILLO = 'ff00ffff'

    ICONO = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
    def __init__(self, nombreArchivoXML):
        """
        Carga el XML en memoria (árbol DOM) y crea el elemento raíz del KML.
        """
        self.arbol = ET.parse(nombreArchivoXML)
        self.raizXML = self.arbol.getroot()

        self.raiz = ET.Element('kml', xmlns=self.NS_KML)
        self.doc = ET.SubElement(self.raiz, 'Document')

        # Puntos de la línea de la ruta: (distancia en km, longitud, latitud, altitud)
        self.ruta = []

        self.addEstilos()

    # ------------------------------------------------------------------
    # Generación de KML
    # ------------------------------------------------------------------
    def addEstilo(self, identificador, color, escala='1.1'):
        """
        Añade un <Style> con un icono de color
        """
        estilo = ET.SubElement(self.doc, 'Style', id=identificador)
        icono = ET.SubElement(estilo, 'IconStyle')
        ET.SubElement(icono, 'color').text = color
        ET.SubElement(icono, 'scale').text = escala
        ET.SubElement(ET.SubElement(icono, 'Icon'), 'href').text = self.ICONO

    def addEstilos(self):
        """
        Define los estilos de cada tipo de punto
        """
        self.addEstilo('salidaMeta', self.ROJO, '1.4')
        self.addEstilo('puerto', self.VERDE, '1.2')
        self.addEstilo('sprint', self.AZUL, '1.2')
        self.addEstilo('anonimo', self.AMARILLO, '0.8')

        estilo = ET.SubElement(self.doc, 'Style', id='ruta')
        linea = ET.SubElement(estilo, 'LineStyle')
        ET.SubElement(linea, 'color').text = 'ff0000ff'
        ET.SubElement(linea, 'width').text = '3'

    def addPlacemark(self, nombre, descripcion, long, lat, alt, estilo,
                     modoAltitud='clampToGround'):
        """
        Añade un elemento <Placemark> con un punto <Point>
        """
        pm = ET.SubElement(self.doc, 'Placemark')
        ET.SubElement(pm, 'name').text = nombre
        ET.SubElement(pm, 'description').text = descripcion
        ET.SubElement(pm, 'styleUrl').text = '#' + estilo
        punto = ET.SubElement(pm, 'Point')
        ET.SubElement(punto, 'altitudeMode').text = modoAltitud
        ET.SubElement(punto, 'coordinates').text = '{},{},{}'.format(long, lat, alt)

    def addLineString(self, nombre, extrude, tesela, listaCoordenadas,
                      modoAltitud, estilo):
        """
        Añade un elemento <Placemark> con una línea <LineString>
        """
        pm = ET.SubElement(self.doc, 'Placemark')
        ET.SubElement(pm, 'name').text = nombre
        ET.SubElement(pm, 'styleUrl').text = '#' + estilo
        ls = ET.SubElement(pm, 'LineString')
        ET.SubElement(ls, 'extrude').text = extrude
        ET.SubElement(ls, 'tessellate').text = tesela
        ET.SubElement(ls, 'altitudeMode').text = modoAltitud
        ET.SubElement(ls, 'coordinates').text = listaCoordenadas

    # ------------------------------------------------------------------
    # Lectura del XML mediante XPath
    # ------------------------------------------------------------------
    def texto(self, nodo, ruta):
        """
        Devuelve el texto del primer elemento que cumple la expresión XPath
        (relativa a nodo), o None si no existe
        """
        hijo = nodo.find(ruta, self.NS_XML)
        return hijo.text.strip() if hijo is not None and hijo.text else None

    def distancia(self, nodo, defecto=0.0):
        """
        Devuelve la distancia (km) de un hito como float
        """
        valor = self.texto(nodo, 'u:distancia')
        return float(valor) if valor is not None else defecto

    def cargarDatosEtapa(self):
        """
        Obtiene número, nombre, inicio, fin y longitud de la etapa
        """
        etapa = self.raizXML.find('.//u:etapa', self.NS_XML)
        self.numero = etapa.get('numero')
        self.nombre = self.texto(etapa, 'u:nombre')
        self.inicio = self.texto(etapa, 'u:inicio')
        self.fin = self.texto(etapa, 'u:fin')
        self.longitudEtapa = float(self.texto(etapa, 'u:longitud'))
        ET.SubElement(self.doc, 'name').text = 'Etapa {}: {}'.format(self.numero, self.nombre)

    def cargarSalida(self):
        """
        Punto de salida (rojo)
        """
        for p in self.raizXML.findall('.//u:lugarSalida', self.NS_XML):
            lon, lat, alt = (self.texto(p, 'u:longitud'), self.texto(p, 'u:latitud'),
                             self.texto(p, 'u:altitud'))
            self.addPlacemark('Salida: ' + self.inicio, 'Salida de la etapa {} (km 0)'.format(self.numero),
                              lon, lat, alt, 'salidaMeta')
            self.ruta.append((0.0, lon, lat, alt))

    def cargarMeta(self):
        """
        Punto de meta (rojo)
        """
        for p in self.raizXML.findall('.//u:lugarEntrada', self.NS_XML):
            lon, lat, alt = (self.texto(p, 'u:longitud'), self.texto(p, 'u:latitud'),
                             self.texto(p, 'u:altitud'))
            self.addPlacemark('Meta: ' + self.fin,
                              'Meta de la etapa {} (km {})'.format(self.numero, self.longitudEtapa),
                              lon, lat, alt, 'salidaMeta')
            self.ruta.append((self.longitudEtapa, lon, lat, alt))

    def cargarPuertos(self):
        """
        Puertos de montaña (verde)
        """
        for p in self.raizXML.findall('.//u:hitos/u:puertosMontana/u:puertoMontana', self.NS_XML):
            lon, lat, alt = (self.texto(p, 'u:longitud'), self.texto(p, 'u:latitud'),
                             self.texto(p, 'u:altitud'))
            km = self.distancia(p)
            self.addPlacemark('Puerto cat. {} (km {})'.format(p.get('categoria'), km),
                              'Puerto de montaña de categoría {}, altitud {} m'.format(p.get('categoria'), alt),
                              lon, lat, alt, 'puerto')

    def cargarSprints(self):
        """
        Sprints intermedio y bonificado (azul)
        """
        for etiqueta, titulo in (('sprintIntermedio', 'Sprint intermedio'),
                                 ('sprintBonificado', 'Sprint bonificado')):
            for p in self.raizXML.findall('.//u:hitos/u:' + etiqueta, self.NS_XML):
                lon, lat, alt = (self.texto(p, 'u:longitud'), self.texto(p, 'u:latitud'),
                                 self.texto(p, 'u:altitud'))
                km = self.distancia(p)
                self.addPlacemark('{} (km {})'.format(titulo, km), titulo, lon, lat, alt, 'sprint')

    def cargarPuntosAnonimos(self):
        """
        Puntos anónimos (amarillo) que se usan para aproximar el trazado
        """
        for p in self.raizXML.findall('.//u:puntosAnonimos/u:puntoAnonimo', self.NS_XML):
            lon, lat, alt = (self.texto(p, 'u:longitud'), self.texto(p, 'u:latitud'),
                             self.texto(p, 'u:altitud'))
            km = self.distancia(p)
            self.addPlacemark('Km {}'.format(km), 'Punto intermedio de la ruta', lon, lat, alt, 'anonimo')
            self.ruta.append((km, lon, lat, alt))

    def addRuta(self):
        """
        Dibuja una línea que une salida, puntos anónimos (ordenados por
        distancia) y meta. Los puertos y sprints solo se marcan con puntos,
        porque sus coordenadas son aproximadas y harían zigzaguear la línea
        """
        coordenadas = []
        for km, lon, lat, alt in sorted(self.ruta, key=lambda punto: punto[0]):
            cadena = '{},{},{}'.format(lon, lat, alt)
            if not coordenadas or coordenadas[-1] != cadena:
                coordenadas.append(cadena)
        self.addLineString('Ruta de la etapa {}'.format(self.numero), '0', '1',
                           '\n'.join(coordenadas), 'clampToGround', 'ruta')

    def cargarPuntos(self):
        """
        Lee todos los datos del XML y construye el KML
        """
        self.cargarDatosEtapa()
        self.cargarSalida()
        self.cargarPuertos()
        self.cargarSprints()
        self.cargarPuntosAnonimos()
        self.cargarMeta()
        self.addRuta()

    # ------------------------------------------------------------------
    # Salida
    # ------------------------------------------------------------------
    def escribir(self, nombreArchivoKML):
        """
        Escribe el archivo KML con declaración y codificación
        """
        arbol = ET.ElementTree(self.raiz)
        ET.indent(arbol)
        arbol.write(nombreArchivoKML, encoding='utf-8', xml_declaration=True)

    def ver(self):
        """
        Muestra el contenido del KML. Se utiliza para depurar
        """
        print("\nElemento raiz = ", self.raiz.tag)
        print("Atributos = ", self.raiz.attrib)
        for hijo in self.raiz.findall('.//Placemark'):
            nombre = hijo.find('name').text
            estilo = hijo.find('styleUrl').text
            tipo = 'Línea' if hijo.find('LineString') is not None else 'Punto'
            print("{:6s} {:10s} {}".format(tipo, estilo, nombre))

def main():
    
    nombreXML = 'etapaEsquema.xml'
    nombreKML = 'etapa.kml'

    nuevoKML = Kml(nombreXML)

    nuevoKML.cargarPuntos()
    
    """Visualización del KML creado"""
    nuevoKML.ver()
    
    """Creación del archivo en formato KML"""
    nuevoKML.escribir(nombreKML)
    print("Creado el archivo: ", nombreKML)
    
if __name__ == "__main__":
    main()    
