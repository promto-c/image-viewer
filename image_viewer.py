import sys
import cv2
import numpy as np

from typing import Tuple, List

from OpenGL import GL
from PyQt5 import QtCore, QtGui, QtWidgets

class LineLayer:
    def __init__(self, line_start, line_end, line_width=2.0, line_color=(1.0, 0.0, 0.0)):
        self.line_start = line_start
        self.line_end = line_end
        self.line_width = line_width
        self.line_color = line_color

    def render(self):
        # Set the line width to the calculated pixel size
        GL.glLineWidth(self.line_width)

        # Draw the line
        GL.glColor3f(*self.line_color)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(*self.line_start)
        GL.glVertex2f(*self.line_end)
        GL.glEnd()

        # Reset the color to white
        GL.glColor3f(1.0, 1.0, 1.0)

class ImageViewerGLWidget(QtWidgets.QOpenGLWidget):

    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0

    ZOOM_STEP = 0.1

    def __init__(self, parent=None, image=None):
        super(ImageViewerGLWidget, self).__init__(parent)

        self.image = image
        self.image_height, self.image_width, _c = self.image.shape

        self.zoom = 1.0

        self.drag_offset = (0.0, 0.0)
        self.drag_start = None
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.texture_id = None

        # test draw line
        self.line_start = None
        self.line_end = None

        self.line_layers: List[LineLayer] = list()

    def sizeHint(self):
        return QtCore.QSize(self.image_width, self.image_height)

    def set_image(self, image_data: np.ndarray) -> None:

        self.image = image_data
        # Get the height and width of the image
        height, width, _channel = self.image.shape
        
        # Flip the image vertically using OpenCV's flip function
        image_data = cv2.flip(self.image, 0)

        # Check the data type of the image and set the corresponding pixel data type and texture format for OpenGL
        if image_data.dtype == np.uint8:
            pixel_data_type = GL.GL_UNSIGNED_BYTE
            texture_format = GL.GL_RGB
        elif image_data.dtype == np.float32:
            pixel_data_type = GL.GL_FLOAT
            texture_format = GL.GL_RGB32F
        else:
            # Return early if the data type is not supported
            return

        # Create an OpenGL texture ID and bind the texture
        self.texture_id = self.gl.glGenTextures(1)

        #
        self.gl.glBindTexture(GL.GL_TEXTURE_2D, self.texture_id)

        # Set the texture minification/magnification filter
        self.gl.glTexParameterf(
            GL.GL_TEXTURE_2D,
            GL.GL_TEXTURE_MIN_FILTER,
            GL.GL_NEAREST
        )
        self.gl.glTexParameterf(
            GL.GL_TEXTURE_2D,
            GL.GL_TEXTURE_MAG_FILTER,
            GL.GL_NEAREST
        )
        
        # Use glTexImage2D to set the image texture in OpenGL
        self.gl.glTexImage2D(
            self.gl.GL_TEXTURE_2D,          # target
            0,                              # level
            texture_format,                 # internal format
            width, height,                  # width and height of the texture
            0,                              # border (must be 0)
            self.gl.GL_RGB,                 # format of the pixel data
            pixel_data_type,                # data type of the pixel data
            image_data.flatten().tolist()   # flattened image data as a list
        )

        self.update()

    def pixel_to_gl_coords(self, pixel_coords: QtCore.QPoint) -> Tuple[float, float]:
        # Calculate the scaled width and height of the image
        scaled_width = self.image_width * self.zoom
        scaled_height = self.image_height * self.zoom

        # Calculate the x and y offsets to center the image
        x_offset = (self.width() - scaled_width) / 2 + self.drag_offset[0]
        y_offset = (self.height() - scaled_height) / 2 - self.drag_offset[1]

        # Calculate the x and y coordinates in GL space
        x = (pixel_coords.x() - x_offset) / self.zoom
        y = (self.height() - pixel_coords.y() - y_offset) / self.zoom

        # Flip the y-coordinate
        y = self.image_height - y

        return x, y

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:

        if event.button() == QtCore.Qt.MiddleButton:
            self.drag_start = (event.x(), event.y())
            self.prev_drag_offset = self.drag_offset
    
        elif event.button() == QtCore.Qt.LeftButton:
            self.line_start = self.pixel_to_gl_coords(event.pos())

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.line_end = self.pixel_to_gl_coords(event.pos())

            line = LineLayer(line_start=self.line_start, line_end=self.line_end)
            self.line_layers.append(line)

            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() & QtCore.Qt.MiddleButton and self.drag_start:
            x_offset = event.x() - self.drag_start[0]
            y_offset = event.y() - self.drag_start[1]
            self.drag_offset = (self.prev_drag_offset[0] + x_offset, self.prev_drag_offset[1] + y_offset)
            self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        ''' Method to handle wheel events
        '''
        # Calculate the zoom delta based on the scroll direction
        zoom_delta = self.ZOOM_STEP if event.angleDelta().y() > 0 else -self.ZOOM_STEP

        # Update the zoom level and clamp it within the minimum and maximum zoom factors
        self.zoom = self.clamp(self.zoom + zoom_delta, self.MIN_ZOOM, self.MAX_ZOOM)

        # Update the widget to apply the zoom transformation
        self.update()

    @staticmethod
    def clamp(value: float, min_value: float, max_value: float) -> float:
        ''' Helper method to clamp a value between a minimum and maximum value
        '''
        return max(min(value, max_value), min_value)

    def fit_image_in_view(self):
        ''' Fits the image within the widget view while maintaining the aspect ratio.
        '''
        # Calculate the new zoom level while preserving the aspect ratio
        self.zoom = min(self.width() / self.image_width, self.height() / self.image_height)

        # Reset the drag offset
        self.drag_offset = (0.0, 0.0)

        # Update the widget to reset the zoom level and offset
        self.update()

    def resizeGL(self, width: int, height: int) -> None:
        ''' Method to handle resizing of the widget

        Args:
            width: The new width of the widget.
            height: The new height of the widget.
        '''
        # Set the viewport to the new width and height of the widget
        self.gl.glViewport(0, 0, width, height)

        # Call the fit_image_in_view method to adjust the zoom level and drag offset
        self.fit_image_in_view()

    def initializeGL(self):
        # Create an OpenGL version profile and set its version
        version_profile = QtGui.QOpenGLVersionProfile()
        version_profile.setVersion(2, 0)

        # Retrieve the OpenGL functions for the given version profile
        self.gl: GL = self.context().versionFunctions(version_profile)

        # Set the clear color for the OpenGL context
        self.gl.glClearColor(0.0, 0.0, 0.0, 1.0)

        # Enable texture mapping
        self.gl.glEnable(GL.GL_TEXTURE_2D)

        # Set the image to display
        self.set_image(self.image)

    def resizeGL(self, width: int, height: int) -> None:
        self.gl.glViewport(0, 0, width, height)

    def paintGL(self) -> None:
        # Clear the buffer
        self.gl.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        #
        self.gl.glBindTexture(GL.GL_TEXTURE_2D, self.texture_id)

        # Set the viewport
        # self.gl.glViewport(0, 0, self.width(), self.height())

        # Set the projection matrix
        self.gl.glMatrixMode(GL.GL_PROJECTION)
        self.gl.glLoadIdentity()
        self.gl.glOrtho(0, self.width(), self.height(), 0, -1, 1)

        # Set the modelview matrix
        self.gl.glMatrixMode(GL.GL_MODELVIEW)
        self.gl.glLoadIdentity()

        # Calculate the scaled width and height of the image
        scaled_width = self.image_width * self.zoom
        scaled_height = self.image_height * self.zoom

        # Calculate the x and y offsets to center the image
        x_offset = (self.width() - scaled_width) / 2 + self.drag_offset[0]
        y_offset = (self.height() - scaled_height) / 2 + self.drag_offset[1]

        # Apply the translation and scaling transformations
        self.gl.glTranslatef(x_offset, y_offset, 0.0)
        self.gl.glScalef(self.zoom, self.zoom, 1.0)

        # NOTE: This part should be grouped as render() method of imageLayer
        # Draw the image quad
        self.gl.glBegin(GL.GL_QUADS)
        self.gl.glTexCoord2f(0.0, 1.0)
        self.gl.glVertex2f(0.0, 0.0)
        self.gl.glTexCoord2f(1.0, 1.0)
        self.gl.glVertex2f(self.image_width, 0.0)
        self.gl.glTexCoord2f(1.0, 0.0)
        self.gl.glVertex2f(self.image_width, self.image_height)
        self.gl.glTexCoord2f(0.0, 0.0)
        self.gl.glVertex2f(0.0, self.image_height)
        self.gl.glEnd()

        # Draw the line
        if self.line_layers:
            for line in self.line_layers:
                line.render()

        # Flush the OpenGL pipeline to ensure that all commands are executed
        self.gl.glFlush()

class MainUI(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(MainUI, self).__init__(parent)

        image_path = r'example_image.1001.jpg'
        image_path2 = r'example_image.1002.jpg'

        image = cv2.imread(image_path)
        self.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # self.image = self.image.astype(np.float32) / 255.0

        image2 = cv2.imread(image_path2)
        self.image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)
        self.image2 = self.image2.astype(np.float32) / 255.0

        self.setup_ui()

    def setup_ui(self):
        self.gl_widget = ImageViewerGLWidget(self, image=self.image)
        self.switch_button = QtWidgets.QPushButton("Switch Image", self)
        self.switch_button.clicked.connect(self.switch_image)

        self.main_layout = QtWidgets.QGridLayout()
        self.main_layout.addWidget(self.gl_widget, 0, 0)
        self.main_layout.addWidget(self.switch_button, 1, 0)
        self.setLayout(self.main_layout)

    def switch_image(self):
        if np.array_equal(self.gl_widget.image, self.image):
            self.gl_widget.set_image(self.image2)
        else:
            self.gl_widget.set_image(self.image)

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    win = MainUI()
    win.show()
    sys.exit( app.exec() )
