# xml2altimetria.py
# -*- coding: utf-8 -*-
"""
Genera el archivo altimetria.svg (perfil altimétrico de la etapa) a partir
de etapaEsquema.xml.

- Toda la información se obtiene del árbol DOM mediante expresiones XPath.
- Programa totalmente orientado a objetos (todas las funciones son métodos).
- El perfil es una polilínea cerrada y rellena (efecto suelo) cuyos vértices
  son la salida, los puntos anónimos, los hitos (puertos y sprints) y la meta.

Basado en 02030-SVG.py de Juan Manuel Cueva Lovelle (Universidad de Oviedo).
"""

import xml.etree.ElementTree as ET


class Svg(object):
    """
    Genera archivos SVG con rectángulos, círculos, líneas, polilíneas y texto
    """

    def __init__(self, ancho, alto):
        """
        Crea el elemento raíz, el espacio de nombres, la versión y el viewBox
        """
        self.raiz = ET.Element('svg',
                               xmlns="http://www.w3.org/2000/svg",
                               version="1.1",
                               width=str(ancho),
                               height=str(alto),
                               viewBox="0 0 {} {}".format(ancho, alto))

    def addRect(self, x, y, width, height, fill, strokeWidth, stroke):
        """
        Añade un elemento rect
        """
        ET.SubElement(self.raiz, 'rect', {
            'x': str(x), 'y': str(y), 'width': str(width), 'height': str(height),
            'fill': fill, 'stroke-width': str(strokeWidth), 'stroke': stroke})

    def addCircle(self, cx, cy, r, fill, stroke='none', strokeWidth='0'):
        """
        Añade un elemento circle
        """
        ET.SubElement(self.raiz, 'circle', {
            'cx': '{:.1f}'.format(cx), 'cy': '{:.1f}'.format(cy), 'r': str(r),
            'fill': fill, 'stroke': stroke, 'stroke-width': str(strokeWidth)})

    def addLine(self, x1, y1, x2, y2, stroke, strokeWidth, dash=None):
        """
        Añade un elemento line (opcionalmente discontinua)
        """
        atributos = {'x1': '{:.1f}'.format(x1), 'y1': '{:.1f}'.format(y1),
                     'x2': '{:.1f}'.format(x2), 'y2': '{:.1f}'.format(y2),
                     'stroke': stroke, 'stroke-width': str(strokeWidth)}
        if dash:
            atributos['stroke-dasharray'] = dash
        ET.SubElement(self.raiz, 'line', atributos)

    def addPolyline(self, points, stroke, strokeWidth, fill):
        """
        Añade un elemento polyline
        """
        ET.SubElement(self.raiz, 'polyline', {
            'points': points, 'stroke': stroke, 'stroke-width': str(strokeWidth),
            'fill': fill, 'stroke-linejoin': 'round'})

    def addText(self, texto, x, y, fontFamily, fontSize, style,
                anchor='start', rotacion=None, fill='#222222', peso='normal'):
        """
        Añade un elemento texto (rotacion en grados alrededor de (x, y))
        """
        atributos = {'x': '{:.1f}'.format(x), 'y': '{:.1f}'.format(y),
                     'font-family': fontFamily, 'font-size': str(fontSize),
                     'font-weight': peso, 'text-anchor': anchor, 'fill': fill,
                     'style': style}
        if rotacion is not None:
            atributos['transform'] = 'rotate({} {:.1f} {:.1f})'.format(rotacion, x, y)
        ET.SubElement(self.raiz, 'text', atributos).text = texto

    def escribir(self, nombreArchivoSVG):
        """
        Escribe el archivo SVG con declaración y codificación
        """
        arbol = ET.ElementTree(self.raiz)
        ET.indent(arbol)
        arbol.write(nombreArchivoSVG, encoding='utf-8', xml_declaration=True)

    def ver(self):
        """
        Muestra un resumen del SVG. Se utiliza para depurar
        """
        print("\nElemento raiz = ", self.raiz.tag)
        print("Atributos = ", self.raiz.attrib)
        recuento = {}
        for hijo in self.raiz.findall('.//*'):
            recuento[hijo.tag] = recuento.get(hijo.tag, 0) + 1
        for etiqueta, veces in recuento.items():
            print("{:10s} x {}".format(etiqueta, veces))


class Altimetria(object):
    """
    Lee los datos de la etapa del XML (XPath) y dibuja el perfil altimétrico
    """

    NS_XML = {'u': 'http://www.uniovi.es'}
    FUENTE = 'Verdana, Arial, sans-serif'

    ROJO = '#e03030'
    VERDE = '#2e9e44'
    AZUL = '#2a7fd4'

    # Tamaño del dibujo y márgenes (píxeles)
    ANCHO, ALTO = 1300, 720
    IZQ, DER, ARRIBA, ABAJO = 95, 60, 360, 80

    def __init__(self, nombreArchivoXML):
        """
        Carga el XML en memoria (árbol DOM)
        """
        self.raizXML = ET.parse(nombreArchivoXML).getroot()
        self.puntos = {}  # distancia (km) -> {'alt': m, 'etiquetas': [...], 'color': ...}
        self.svg = Svg(self.ANCHO, self.ALTO)

    # ------------------------------------------------------------------
    # Lectura del XML mediante XPath
    # ------------------------------------------------------------------
    def texto(self, nodo, ruta):
        """
        Texto del primer elemento que cumple la expresión XPath (relativa a nodo)
        """
        hijo = nodo.find(ruta, self.NS_XML)
        return hijo.text.strip() if hijo is not None and hijo.text else None

    def addPunto(self, km, altitud, etiqueta=None, color=None):
        """
        Registra un punto del perfil. Si ya hay uno en el mismo km se fusionan
        sus etiquetas (por ejemplo, los dos sprints o puerto y meta)
        """
        km = round(float(km), 1)
        punto = self.puntos.setdefault(km, {'alt': float(altitud), 'etiquetas': [], 'color': None})
        if etiqueta:
            punto['etiquetas'].append(etiqueta)
        if color and (punto['color'] is None or color == self.ROJO):
            punto['color'] = color

    def cargarDatosEtapa(self):
        """
        Número, nombre, longitud y desnivel de la etapa
        """
        etapa = self.raizXML.find('.//u:etapa', self.NS_XML)
        self.numero = etapa.get('numero')
        self.nombre = self.texto(etapa, 'u:nombre')
        self.inicio = self.texto(etapa, 'u:inicio')
        self.fin = self.texto(etapa, 'u:fin')
        self.longitud = float(self.texto(etapa, 'u:longitud'))
        self.desnivel = self.texto(etapa, 'u:desnivel')

    def cargarSalidaMeta(self):
        """
        Salida (km 0) y meta (km = longitud de la etapa)
        """
        for p in self.raizXML.findall('.//u:lugarSalida', self.NS_XML):
            self.addPunto(0, self.texto(p, 'u:altitud'), 'Salida: ' + self.inicio, self.ROJO)
        for p in self.raizXML.findall('.//u:lugarEntrada', self.NS_XML):
            self.addPunto(self.longitud, self.texto(p, 'u:altitud'), 'Meta: ' + self.fin, self.ROJO)

    def cargarPuertos(self):
        """
        Puertos de montaña
        """
        for p in self.raizXML.findall('.//u:hitos/u:puertosMontana/u:puertoMontana', self.NS_XML):
            self.addPunto(self.texto(p, 'u:distancia'), self.texto(p, 'u:altitud'),
                          'Puerto cat. ' + p.get('categoria'), self.VERDE)

    def cargarSprints(self):
        """
        Sprints intermedio y bonificado
        """
        for etiqueta, titulo in (('sprintIntermedio', 'Sprint intermedio'),
                                 ('sprintBonificado', 'Sprint bonificado')):
            for p in self.raizXML.findall('.//u:hitos/u:' + etiqueta, self.NS_XML):
                self.addPunto(self.texto(p, 'u:distancia'), self.texto(p, 'u:altitud'),
                              titulo, self.AZUL)

    def cargarPuntosAnonimos(self):
        """
        Puntos anónimos (solo dan forma al perfil, sin etiqueta)
        """
        for p in self.raizXML.findall('.//u:puntosAnonimos/u:puntoAnonimo', self.NS_XML):
            self.addPunto(self.texto(p, 'u:distancia'), self.texto(p, 'u:altitud'))

    def cargarDatos(self):
        """
        Lee todos los datos necesarios del XML
        """
        self.cargarDatosEtapa()
        self.cargarSalidaMeta()
        self.cargarPuertos()
        self.cargarSprints()
        self.cargarPuntosAnonimos()

        # Escala vertical: de 0 al máximo redondeado hacia arriba a múltiplo de 500
        maximo = max(p['alt'] for p in self.puntos.values())
        self.altMax = (int(maximo // 500) + 1) * 500

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def x(self, km):
        """
        Convierte kilómetros en coordenada X
        """
        return self.IZQ + km / self.longitud * (self.ANCHO - self.IZQ - self.DER)

    def y(self, altitud):
        """
        Convierte metros de altitud en coordenada Y
        """
        base = self.ALTO - self.ABAJO
        return base - altitud / self.altMax * (base - self.ARRIBA)

    def dibujarFondoYCuadricula(self):
        """
        Fondo blanco, título, líneas horizontales de altitud y escala vertical
        """
        s = self.svg
        s.addRect(0, 0, self.ANCHO, self.ALTO, 'white', 0, 'none')
        s.addText('Etapa {}: {}'.format(self.numero, self.nombre), self.IZQ, 34,
                  self.FUENTE, 22, 'none', peso='bold')
        s.addText('Distancia: {} km   ·   Desnivel positivo: {}'.format(self.longitud, self.desnivel),
                  self.IZQ, 58, self.FUENTE, 14, 'none')

        for alt in range(0, self.altMax + 1, 500):
            s.addLine(self.x(0), self.y(alt), self.x(self.longitud), self.y(alt),
                      '#d0d0d0', 1, '4 4')
            s.addText('{}'.format(alt), self.x(0) - 8, self.y(alt) + 4,
                      self.FUENTE, 12, 'none', anchor='end')
        s.addText('Altitud (m)', 28, (self.ARRIBA + self.ALTO - self.ABAJO) / 2,
                  self.FUENTE, 13, 'none', anchor='middle', rotacion=-90)

    def dibujarPerfil(self):
        """
        Polilínea cerrada y rellena con los puntos (km, altitud) ordenados por km
        """
        base = self.y(0)
        ordenados = sorted(self.puntos.items())
        vertices = ['{:.1f},{:.1f}'.format(self.x(0), base)]
        vertices += ['{:.1f},{:.1f}'.format(self.x(km), self.y(p['alt'])) for km, p in ordenados]
        vertices += ['{:.1f},{:.1f}'.format(self.x(self.longitud), base),
                     '{:.1f},{:.1f}'.format(self.x(0), base)]
        self.svg.addPolyline(' '.join(vertices), '#9c2a14', 2, '#e8452c')

    def dibujarHitos(self):
        """
        Líneas verticales, marcadores y textos verticales de los hitos
        """
        s = self.svg
        for km, p in sorted(self.puntos.items()):
            if not p['etiquetas']:
                continue
            xp, yp = self.x(km), self.y(p['alt'])
            s.addLine(xp, self.ARRIBA - 6, xp, yp, p['color'], 1.5)
            s.addCircle(xp, yp, 6, p['color'], 'white', 2)
            etiqueta = ' + '.join(p['etiquetas']) + ' / {:.0f} m'.format(p['alt'])
            s.addText(etiqueta, xp + 4, self.ARRIBA - 12, self.FUENTE, 12, 'none',
                      rotacion=-90)

    def dibujarEjes(self):
        """
        Eje horizontal con la escala de distancia en km
        """
        s = self.svg
        base = self.y(0)
        s.addLine(self.x(0), base, self.x(self.longitud), base, '#222222', 2)
        s.addLine(self.x(0), self.y(self.altMax), self.x(0), base, '#222222', 2)

        # Marcas cada 20 km y la meta (se omite la marca que quede pegada a la meta)
        marcas = [float(km) for km in range(0, int(self.longitud) + 1, 20)
                  if self.longitud - km > 8] + [self.longitud]
        for km in marcas:
            s.addLine(self.x(km), base, self.x(km), base + 6, '#222222', 1.5)
            s.addText('{:g}'.format(km), self.x(km), base + 22, self.FUENTE, 12, 'none',
                      anchor='middle')
        s.addText('Distancia (km)', (self.x(0) + self.x(self.longitud)) / 2, base + 50,
                  self.FUENTE, 13, 'none', anchor='middle')

    def dibujar(self):
        """
        Construye el SVG completo
        """
        self.dibujarFondoYCuadricula()
        self.dibujarPerfil()
        self.dibujarHitos()
        self.dibujarEjes()

    def escribir(self, nombreArchivoSVG):
        """
        Escribe el archivo SVG
        """
        self.svg.escribir(nombreArchivoSVG)

    def ver(self):
        """
        Muestra un resumen del SVG creado
        """
        self.svg.ver()


class Programa(object):
    """
    Punto de entrada (para que no haya funciones fuera de clases)
    """

    XML_POR_DEFECTO = 'etapaEsquema.xml'
    SVG_POR_DEFECTO = 'altimetria.svg'

    @staticmethod
    def main(argumentos):
        nombreXML = argumentos[1] if len(argumentos) > 1 else Programa.XML_POR_DEFECTO
        nombreSVG = argumentos[2] if len(argumentos) > 2 else Programa.SVG_POR_DEFECTO

        altimetria = Altimetria(nombreXML)
        altimetria.cargarDatos()
        altimetria.dibujar()
        altimetria.ver()
        altimetria.escribir(nombreSVG)
        print("\nCreado el archivo: ", nombreSVG)

def main():
    altimetria = Altimetria("etapaEsquema.xml")
    altimetria.cargarDatos()
    altimetria.dibujar()
    altimetria.ver()
    altimetria.escribir("altimetria.svg")


if __name__ == "__main__":
    main()
