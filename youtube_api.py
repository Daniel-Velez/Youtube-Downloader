import os
import re
import sys
import requests
import zipfile
import shutil
from dotenv import load_dotenv 
from pytube import YouTube
from googleapiclient.discovery import build
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, QPushButton, 
                             QVBoxLayout, QWidget, QFileDialog, QMessageBox, QListWidget, 
                             QListWidgetItem, QHBoxLayout, QSizePolicy)



load_dotenv()

# Leer la clave de la API de YouTube desde las variables de entorno
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
# Obtener la ruta de la carpeta de descargas predeterminada
if sys.platform == 'win32':
    default_download_folder = os.path.join(os.environ['USERPROFILE'], 'Downloads')
elif sys.platform == 'darwin':
    default_download_folder = os.path.join(os.environ['HOME'], 'Downloads')
else:
    default_download_folder = os.path.join(os.environ['HOME'], 'Downloads')

# Versión actual de la aplicación
CURRENT_VERSION = "1.0.1"

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class YouTubeDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_folder = default_download_folder
        self.initUI()
        self.check_for_updates()

    def initUI(self):
        self.setWindowTitle('Youtube Downloader')
        self.setGeometry(100, 100, 450, 600)
        self.setFixedSize(450, 600)

        # Verificación del icono
        icon_path = resource_path('icono.jpeg')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"El icono no se encontró en la ruta: {icon_path}")

        # Verificación de la imagen de fondo
        background_image_path = resource_path('C:/Users/User/Desktop/Deberes/Programacion_Daniel/Youtube Downloader/Fondo.png')
        print(f"Resolved background image path: {background_image_path}")  # Línea de depuración
        
        if os.path.exists(background_image_path):
            try:
                pixmap = QPixmap(background_image_path)
                if not pixmap.isNull():
                    self.setStyleSheet(f"""
                        QMainWindow {{
                            background-image: url('{background_image_path}');
                            background-position: center;
                            font-family: Arial;
                            font-size: 14px;
                        }}
                        QLabel {{
                            color: black;
                            font-size: 16px;
                        }}
                        QPushButton {{
                            background-color: #00FFCD;
                            color: black;
                            font-size: 14px;
                            border-radius: 5px;
                            padding: 10px;
                        }}
                        QPushButton:pressed {{
                            background-color:  #A3FFED;  /* Color cuando se presiona */
                            QTimer.singleShot(200, lambda: QPushButton.setStyleSheet())
                        }}
                        QLineEdit {{
                            font-size: 14px;
                            padding: 5px;
                        }}
                    """)
                else:
                    print(f"No se pudo crear el QPixmap desde: {background_image_path}")
            except Exception as e:
                print(f"Error al cargar la imagen de fondo: {e}")
        else:
            print(f"La imagen de fondo no se encontró en la ruta: {background_image_path}")
            
        # Crear widgets
        self.url_label = QLabel('URL del video o búsqueda:', self)
        self.url_entry = QLineEdit(self)
        self.url_entry.setStyleSheet("background-color: rgba(255, 255, 255, 100);")
        
        self.buscar_button = QPushButton('Buscar', self)
        self.buscar_button.setFixedWidth(90)
        self.buscar_button.clicked.connect(self.buscar_resultados)

        self.carpeta_button = QPushButton('Seleccionar Carpeta', self)
        self.carpeta_button.setFixedWidth(150)
        self.carpeta_button.clicked.connect(self.seleccionar_carpeta)

        self.carpeta_label = QLabel(f'Carpeta de destino: {self.selected_folder}', self)
        self.carpeta_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.carpeta_label.setWordWrap(True)
        self.carpeta_label.setStyleSheet("background-color: rgba(255, 255, 255, 80); padding: 5px;")

        self.resultados_list = QListWidget(self)
        self.resultados_list.setStyleSheet("background-color: rgba(255, 250, 250, 50);")
        self.resultados_list.itemClicked.connect(self.seleccionar_resultado)

        self.descargar_musica_button = QPushButton('Desc. Música', self)
        self.descargar_musica_button.clicked.connect(self.iniciar_descarga_musica)
        self.descargar_musica_button.setFixedWidth(100)

        self.descargar_video_button = QPushButton('Desc. Video', self)
        self.descargar_video_button.clicked.connect(self.iniciar_descarga_video)
        self.descargar_video_button.setFixedWidth(100)

        # Botón "Buscar más"
        self.buscar_mas_button = QPushButton('Buscar Más', self)
        self.buscar_mas_button.setFixedWidth(100)
        self.buscar_mas_button.clicked.connect(self.buscar_mas_resultados)
        self.buscar_mas_button.pressed.connect(lambda: self.cambiar_color_boton(self.buscar_mas_button))
        self.buscar_mas_button.hide()

        self.buscar_button.pressed.connect(lambda: self.cambiar_color_boton(self.buscar_button))
        self.carpeta_button.pressed.connect(lambda: self.cambiar_color_boton(self.carpeta_button))
        self.descargar_musica_button.pressed.connect(lambda: self.cambiar_color_boton(self.descargar_musica_button))
        self.descargar_video_button.pressed.connect(lambda: self.cambiar_color_boton(self.descargar_video_button))
        self.buscar_mas_button.pressed.connect(lambda: self.cambiar_color_boton(self.buscar_mas_button))

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.url_label)
        layout.addWidget(self.url_entry)
        layout.addWidget(self.carpeta_label)

        search_layout = QHBoxLayout()
        search_layout.addWidget(self.buscar_button)
        search_layout.addWidget(self.carpeta_button)
        layout.addLayout(search_layout)

        # Contenedor para el QListWidget
        list_container = QWidget()
        list_container.setFixedWidth(450)  # Ajusta el ancho del contenedor aquí
        list_container.setStyleSheet("background-color: rgba(255, 255, 255, 100);")
        
        list_layout = QVBoxLayout()
        list_layout.addWidget(self.resultados_list)
        list_container.setLayout(list_layout)
        layout.addWidget(list_container)

        # Layout para los botones en línea
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.buscar_mas_button)
        button_layout.addWidget(self.descargar_musica_button)
        button_layout.addWidget(self.descargar_video_button)
        layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def cambiar_color_boton(self, boton):
        original_style = boton.styleSheet()
        boton.setStyleSheet("background-color:  #A3FFED;")  # Cambia el color del botón cuando se presiona
        QTimer.singleShot(200, lambda: boton.setStyleSheet(original_style))

    def seleccionar_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta", self.selected_folder)
        if carpeta:
            self.selected_folder = carpeta
            self.carpeta_label.setText(f"Carpeta de destino: {carpeta}")

    def iniciar_descarga_musica(self):
        url = self.url_entry.text()
        if 'youtube.com' in url or 'youtu.be' in url:
            resultado = self.descargar_musica(url, self.selected_folder)
            self.mostrar_mensaje(resultado)
        else:
            self.buscar_resultados()

    def iniciar_descarga_video(self):
        url = self.url_entry.text()
        if 'youtube.com' in url or 'youtu.be' in url:
            resultado = self.descargar_video(url, self.selected_folder)
            self.mostrar_mensaje(resultado)
        else:
            self.buscar_resultados()

    def mostrar_mensaje(self, mensaje):
        if "Error" in mensaje:
            QMessageBox.critical(self, "Error", mensaje)
        else:
            QMessageBox.information(self, "Éxito", mensaje)

    def descargar_musica(self, url, carpeta_descargas):
        try:
            video = YouTube(url)
            stream = video.streams.filter(only_audio=True).first()
            titulo_limpio = re.sub(r'[\\/*?:"<>|]', "", video.title)
            stream.download(output_path=carpeta_descargas, filename=f"{titulo_limpio}.mp3")
            return f"Música descargada en: {os.path.join(carpeta_descargas, titulo_limpio + '.mp3')}"
        except Exception as e:
            return f"Error al descargar la música: {e}"

    def descargar_video(self, url, carpeta_descargas):
        try:
            video = YouTube(url)
            streams = video.streams.filter(progressive=True)
            stream = streams.get_by_resolution("720p")
            
            if not stream:
                stream = streams.order_by('resolution').desc().first()
            
            titulo_limpio = re.sub(r'[\\/*?:"<>|]', "", video.title)
            stream.download(output_path=carpeta_descargas, filename=f"{titulo_limpio}.mp4")
            return f"Video descargado en: {os.path.join(carpeta_descargas, titulo_limpio + '.mp4')}"
        except Exception as e:
            return f"Error al descargar el video: {e}"

    def buscar_resultados(self):
        self.query = self.url_entry.text()  # Almacena la consulta en un atributo de instancia
        self.next_page_token = None  # Reiniciar el token de la página siguiente
        self.resultados_list.clear()
        
        # Verificar si la entrada es una URL de YouTube
        if 'youtube.com' in self.query or 'youtu.be' in self.query:
            # Si es una URL, obtener el título del video y agregarlo a la lista
            try:
                video = YouTube(self.query)
                titulo = video.title
                url = self.query
                miniatura_url = video.thumbnail_url
                canal = video.author
                fecha_publicacion = video.publish_date.strftime('%Y-%m-%d')

                item_text = f"{titulo}\n{canal} - {fecha_publicacion}"
                item = QListWidgetItem()
                item.setData(Qt.UserRole, (url, miniatura_url))

                # Crear un widget personalizado para el elemento de la lista
                widget = QWidget()
                layout = QVBoxLayout()

                # Etiqueta para el texto
                text_label = QLabel(item_text)
                text_label.setWordWrap(True)
                text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                text_label.setStyleSheet("QLabel { padding: 5px; }")

                # Etiqueta para la miniatura
                miniatura_label = QLabel()
                miniatura_label.setAlignment(Qt.AlignCenter)
                pixmap = self.obtener_pixmap_miniatura(miniatura_url)
                pixmap = pixmap.scaled(400, 150, Qt.KeepAspectRatio)  # Ajustar tamaño de miniatura
                miniatura_label.setPixmap(pixmap)

                # Añadir etiquetas al layout del widget personalizado
                layout.addWidget(miniatura_label)
                layout.addWidget(text_label)
                widget.setLayout(layout)

                # Añadir el widget personalizado al QListWidgetItem
                item.setSizeHint(widget.sizeHint())
                self.resultados_list.addItem(item)
                self.resultados_list.setItemWidget(item, widget)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al procesar la URL de YouTube: {e}")
        else:
            # Si no es una URL, realizar una búsqueda en YouTube
            self.cargar_resultados(self.query)

    def cargar_resultados(self, query, page_token=None):
        resultados, next_page_token = self.buscar_video_en_youtube(query, page_token)
        for titulo, url, miniatura_url, canal, fecha_publicacion in resultados:
            item_text = f"{titulo}\n{canal} - {fecha_publicacion}"
            item = QListWidgetItem()
            item.setData(Qt.UserRole, (url, miniatura_url))

            # Crear un widget personalizado para el elemento de la lista
            widget = QWidget()
            layout = QVBoxLayout()

            # Etiqueta para el texto
            text_label = QLabel(item_text)
            text_label.setWordWrap(True)
            text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            text_label.setStyleSheet("QLabel { padding: 0px; }")

            # Etiqueta para la miniatura
            miniatura_label = QLabel()
            miniatura_label.setAlignment(Qt.AlignCenter)
            pixmap = self.obtener_pixmap_miniatura(miniatura_url)
            pixmap = pixmap.scaled(400, 150, Qt.KeepAspectRatio)  # Ajustar tamaño de miniatura
            miniatura_label.setPixmap(pixmap)

            # Añadir etiquetas al layout del widget personalizado
            layout.addWidget(miniatura_label)
            layout.addWidget(text_label)
            widget.setLayout(layout)

            # Añadir el widget personalizado al QListWidgetItem
            item.setSizeHint(widget.sizeHint())
            self.resultados_list.addItem(item)
            self.resultados_list.setItemWidget(item, widget)

        # Mostrar el botón "Buscar más" si hay más resultados
        if next_page_token:
            self.next_page_token = next_page_token
            self.buscar_mas_button.show()
        else:
            self.next_page_token = None
            self.buscar_mas_button.hide()

    def buscar_mas_resultados(self):
        self.cargar_resultados(self.query, self.next_page_token)

    def obtener_pixmap_miniatura(self, url_miniatura):
        try:
            response = requests.get(url_miniatura)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            return pixmap
        except Exception as e:
            print(f"Error al cargar miniatura: {e}")
            return QPixmap()

    def buscar_video_en_youtube(self, query, page_token=None):
        try:
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            request = youtube.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=10,
                pageToken=page_token
            )
            response = request.execute()

            resultados = []
            next_page_token = response.get('nextPageToken', None)
            if response['items']:
                for item in response['items']:
                    video_id = item['id']['videoId']
                    titulo = item['snippet']['title']
                    canal = item['snippet']['channelTitle']
                    miniatura_url = item['snippet']['thumbnails']['medium']['url']
                    fecha_publicacion = item['snippet']['publishedAt'].split('T')[0]
                    resultados.append((titulo, f'https://www.youtube.com/watch?v={video_id}', miniatura_url, canal, fecha_publicacion))
            return resultados, next_page_token
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al buscar en YouTube: {e}")
            return [], None

    def seleccionar_resultado(self, item):
        url, miniatura_url = item.data(Qt.UserRole)
        self.url_entry.setText(url)
        self.mostrar_miniatura(miniatura_url)

    def mostrar_miniatura(self, url_miniatura):
        try:
            response = requests.get(url_miniatura)
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            miniatura_label = QLabel(self)
            miniatura_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error al cargar miniatura: {e}")

    def check_for_updates(self):
        try:
            response = requests.get('https://raw.githubusercontent.com/Daniel-Velez/Youtube-Downloader/main/version.txt')
            last_version = response.text.strip()
            if last_version != CURRENT_VERSION:
                self.prompt_update(CURRENT_VERSION)
        except Exception as e:
            print(f"Error al verificar actualizaciones: {e}")

    def prompt_update(self, CURRENT_VERSION):
        reply = QMessageBox.question(self, 'Actualización Disponible',
                                     f'Hay una nueva versión disponible: {CURRENT_VERSION}. ¿Quieres actualizar?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.update_application()

    def update_application(self):
        temp_dir = 'update_temp'
        
        try:
            # Descargar el archivo zip del repositorio
            response = requests.get('https://github.com/Daniel-Velez/Youtube-Downloader/archive/refs/heads/main.zip')
            response.raise_for_status()  # Manejar errores HTTP
            
            # Guardar el archivo zip en disco
            with open('update.zip', 'wb') as f:
                f.write(response.content)
            
            # Crear un directorio temporal para la actualización
            os.makedirs(temp_dir, exist_ok=True)
            
            # Descomprimir el archivo zip
            with zipfile.ZipFile('update.zip', 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Ruta del contenido descomprimido
            extracted_dir = os.path.join(temp_dir, 'Youtube-Downloader-main')

            # Mover archivos descomprimidos a la ubicación correcta
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    if file == '.gitignore':
                        continue  # Ignorar el archivo .gitignore
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join('.', os.path.relpath(src_file, extracted_dir))
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.move(src_file, dst_file)

            # Eliminar el archivo zip descargado
            os.remove('update.zip')
            
            QMessageBox.information(self, 'Actualización', 'La aplicación se ha actualizado. Reinicia la aplicación.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error al actualizar la aplicación: {e}')
        finally:
            # Eliminar la carpeta temporal
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeDownloader()
    ex.show()
    sys.exit(app.exec_())
