"""
Bot de Citas Automáticas - Ayuntamiento de Madrid
Automatiza la obtención de citas para trámites de Padrón y otros servicios.
"""

import time
import logging
from datetime import datetime
from typing import Optional, List, Callable

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class MadridAppointmentBot:
    """Bot para obtener citas automáticamente en el Ayuntamiento de Madrid."""

    BASE_URL = "https://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do"

    def __init__(self, config: dict, notifier: Optional[Callable] = None):
        """
        Inicializa el bot.

        Args:
            config: Diccionario con la configuración del bot
            notifier: Función opcional para enviar notificaciones
        """
        self.config = config
        self.notifier = notifier
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.cita_conseguida = False

    def _setup_driver(self) -> None:
        """Configura el driver de Selenium."""
        options = Options()

        bot_config = self.config.get('bot', {})

        if bot_config.get('headless', False):
            options.add_argument('--headless=new')

        # Opciones para evitar detección
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Evitar que se detecte como automatizado
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

        # Ejecutar script para ocultar webdriver
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })

        timeout = bot_config.get('timeout', 30)
        self.wait = WebDriverWait(self.driver, timeout)

        logger.info("Driver de Chrome inicializado correctamente")

    def _notify(self, message: str, is_success: bool = False) -> None:
        """Envía una notificación si está configurado."""
        if self.notifier:
            try:
                self.notifier(message, is_success)
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")

    def _safe_click(self, element, retries: int = 3) -> bool:
        """Intenta hacer clic en un elemento de forma segura."""
        for i in range(retries):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                element.click()
                return True
            except ElementClickInterceptedException:
                time.sleep(1)
            except StaleElementReferenceException:
                time.sleep(1)
        return False

    def _wait_and_find(self, by: By, value: str, timeout: int = None) -> Optional[object]:
        """Espera y encuentra un elemento."""
        try:
            wait = WebDriverWait(self.driver, timeout or self.config.get('bot', {}).get('timeout', 30))
            return wait.until(EC.presence_of_element_located((by, value)))
        except TimeoutException:
            return None

    def _wait_and_click(self, by: By, value: str, timeout: int = None) -> bool:
        """Espera a que un elemento sea clickable y hace clic."""
        try:
            wait = WebDriverWait(self.driver, timeout or self.config.get('bot', {}).get('timeout', 30))
            element = wait.until(EC.element_to_be_clickable((by, value)))
            return self._safe_click(element)
        except TimeoutException:
            return False

    def navegar_a_pagina_inicial(self) -> bool:
        """Navega a la página inicial de citas."""
        try:
            logger.info(f"Navegando a {self.BASE_URL}")
            self.driver.get(self.BASE_URL)
            time.sleep(2)

            # Verificar que la página cargó correctamente
            if "tramite" in self.driver.current_url.lower() or "GNSIS" in self.driver.page_source:
                logger.info("Página de citas cargada correctamente")
                return True
            else:
                logger.warning("La página no parece haber cargado correctamente")
                return False

        except Exception as e:
            logger.error(f"Error navegando a la página inicial: {e}")
            return False

    def aceptar_cookies(self) -> bool:
        """Acepta el banner de cookies si aparece."""
        logger.info("Buscando banner de cookies...")

        selectores_cookies = [
            # Específico para Madrid.es - "Aceptar todas"
            (By.XPATH, "//button[text()='Aceptar todas']"),
            (By.XPATH, "//button[contains(text(), 'Aceptar todas')]"),
            # Genéricos
            (By.XPATH, "//button[contains(text(), 'Aceptar')]"),
            (By.XPATH, "//button[contains(text(), 'ACEPTAR')]"),
            (By.ID, "aceptarCookies"),
            (By.ID, "acceptCookies"),
        ]

        for by, value in selectores_cookies:
            try:
                elemento = self.driver.find_element(by, value)
                if elemento.is_displayed():
                    self._safe_click(elemento)
                    logger.info("Cookies aceptadas")
                    time.sleep(1)
                    return True
            except NoSuchElementException:
                continue
            except Exception:
                continue

        logger.info("No se encontró banner de cookies (puede que ya estén aceptadas)")
        return True

    def seleccionar_acceso_sin_identificar(self) -> bool:
        """Selecciona la opción de acceso sin identificar."""
        logger.info("Buscando opción 'Acceso sin identificar'...")

        selectores_acceso = [
            # Específico para Madrid.es - "Acceso SIN Identificar"
            (By.XPATH, "//button[contains(text(), 'SIN Identificar')]"),
            (By.XPATH, "//button[contains(text(), 'Acceso SIN')]"),
            (By.XPATH, "//a[contains(text(), 'SIN Identificar')]"),
            (By.XPATH, "//a[contains(text(), 'Acceso SIN')]"),
            (By.XPATH, "//*[contains(text(), 'Acceso SIN Identificar')]"),
            # Variantes
            (By.XPATH, "//button[contains(text(), 'sin identificar')]"),
            (By.XPATH, "//a[contains(text(), 'sin identificar')]"),
            (By.PARTIAL_LINK_TEXT, "SIN Identificar"),
            (By.PARTIAL_LINK_TEXT, "sin identificar"),
        ]

        for by, value in selectores_acceso:
            try:
                elemento = self.driver.find_element(by, value)
                if elemento.is_displayed():
                    self._safe_click(elemento)
                    logger.info("Acceso sin identificar seleccionado")
                    time.sleep(2)
                    return True
            except NoSuchElementException:
                continue
            except Exception:
                continue

        # Intentar buscar por imagen o icono
        try:
            elementos = self.driver.find_elements(By.TAG_NAME, "a")
            for elem in elementos:
                texto = elem.text.lower()
                if "sin identificar" in texto or "anónimo" in texto or "anonimo" in texto:
                    self._safe_click(elem)
                    logger.info("Acceso sin identificar seleccionado (búsqueda general)")
                    time.sleep(2)
                    return True
        except Exception:
            pass

        logger.warning("No se encontró la opción de acceso sin identificar")
        return False

    def seleccionar_categoria(self) -> bool:
        """Selecciona la categoría del trámite (ej: Padrón y censo)."""
        categoria = self.config.get('tramite', {}).get('categoria', 'Padrón y censo')
        logger.info(f"Buscando categoría: {categoria}")

        try:
            time.sleep(2)

            # Buscar dropdowns Select2
            dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "span.select2-selection")
            if len(dropdowns) >= 1:
                self._safe_click(dropdowns[0])
                time.sleep(1)

                # Escribir en campo de búsqueda
                try:
                    search = self.driver.find_element(By.CSS_SELECTOR, "input.select2-search__field")
                    search.send_keys("Padrón")
                    time.sleep(1)
                except Exception:
                    pass

                # Seleccionar opción
                opciones = self.driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                for op in opciones:
                    if categoria.lower() in op.text.lower() and op.is_displayed():
                        self._safe_click(op)
                        logger.info(f"Categoría seleccionada: {op.text}")
                        time.sleep(1)
                        return True

            # Si ya está seleccionada
            if categoria.lower() in self.driver.page_source.lower():
                logger.info(f"Categoría ya visible: {categoria}")
                return True

            logger.warning(f"No se pudo seleccionar la categoría")
            return False

        except Exception as e:
            logger.error(f"Error seleccionando categoría: {e}")
            return False

    def seleccionar_tramite(self) -> bool:
        """Selecciona el trámite específico."""
        tramite = self.config.get('tramite', {}).get('nombre', 'Altas, bajas y cambio de domicilio en Padrón')
        logger.info(f"Buscando trámite: {tramite}")

        try:
            time.sleep(2)

            # Buscar dropdowns Select2 - el segundo es el de trámite
            dropdowns = self.driver.find_elements(By.CSS_SELECTOR, "span.select2-selection")
            if len(dropdowns) >= 2:
                self._safe_click(dropdowns[1])
                time.sleep(1)

                # Escribir en campo de búsqueda para filtrar
                try:
                    search = self.driver.find_element(By.CSS_SELECTOR, "input.select2-search__field")
                    search.send_keys("Altas")
                    time.sleep(1)
                except Exception:
                    pass

                # Seleccionar opción que contenga el texto
                opciones = self.driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
                for op in opciones:
                    texto = op.text.lower()
                    if "altas" in texto and "padrón" in texto and op.is_displayed():
                        self._safe_click(op)
                        logger.info(f"Trámite seleccionado: {op.text}")
                        time.sleep(1)
                        return True

            # Si ya está seleccionado
            if "altas" in self.driver.page_source.lower() and "padrón" in self.driver.page_source.lower():
                logger.info(f"Trámite ya visible")
                return True

            logger.warning(f"No se pudo seleccionar el trámite")
            return False

        except Exception as e:
            logger.error(f"Error seleccionando trámite: {e}")
            return False

    def click_oficina_cita_temprana(self) -> bool:
        """Hace clic en 'consultar la oficina con cita más temprana'."""
        logger.info("Buscando enlace 'oficina con cita más temprana'...")

        try:
            time.sleep(1)

            # Buscar todos los enlaces en la página
            enlaces = self.driver.find_elements(By.TAG_NAME, "a")
            for enlace in enlaces:
                texto = enlace.text.lower()
                if "temprana" in texto or "más temprana" in texto:
                    self._safe_click(enlace)
                    logger.info(f"Enlace clickeado: {enlace.text}")
                    time.sleep(2)
                    return True

            # También buscar por el icono de calendario que está al lado
            iconos = self.driver.find_elements(By.CSS_SELECTOR, "a i, a img, a svg")
            for icono in iconos:
                padre = icono.find_element(By.XPATH, "..")
                if padre.tag_name == "a":
                    texto_padre = padre.text.lower()
                    href = padre.get_attribute("href") or ""
                    if "temprana" in texto_padre or "temprana" in href:
                        self._safe_click(padre)
                        logger.info("Enlace con icono clickeado")
                        time.sleep(2)
                        return True

            # Buscar cualquier elemento clickeable con "temprana"
            elementos = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'temprana')]")
            for elem in elementos:
                if elem.is_displayed():
                    self._safe_click(elem)
                    logger.info(f"Elemento con 'temprana' clickeado")
                    time.sleep(2)
                    return True

        except Exception as e:
            logger.error(f"Error buscando enlace: {e}")

        logger.warning("No se encontró el enlace de cita más temprana")
        return False

    def verificar_hay_citas_disponibles(self) -> bool:
        """Verifica si hay citas disponibles o aparece mensaje de 'no hay hueco'."""
        logger.info("Verificando si hay citas disponibles...")

        try:
            time.sleep(2)
            page_source = self.driver.page_source.lower()

            # Mensajes que indican que NO hay citas
            mensajes_sin_citas = [
                "no se ha encontrado hueco disponible",
                "no hay citas disponibles",
                "no existen huecos",
                "inténtelo de nuevo más tarde",
                "intentelo de nuevo mas tarde",
                "no hay hueco disponible",
                "seleccione otro trámite",
            ]

            for mensaje in mensajes_sin_citas:
                if mensaje in page_source:
                    logger.info(f"No hay citas: '{mensaje}'")
                    return False

            # Verificar que realmente estamos en una página de citas
            # (debe haber un calendario, campo DNI, o lista de horas)
            indicadores_citas = [
                "calendario",
                "seleccione fecha",
                "seleccione día",
                "horas disponibles",
                "introduzca su dni",
                "introduzca su nif",
            ]

            for indicador in indicadores_citas:
                if indicador in page_source:
                    logger.info(f"¡Hay citas disponibles! Indicador: '{indicador}'")
                    return True

            # Si estamos en la página de selección de trámite sin mensaje de error,
            # puede que aún no hayamos llegado a la verificación
            if "seleccione el trámite" in page_source or "cita previa por trámite" in page_source:
                logger.info("Aún en página de selección de trámite")
                return False

            logger.info("No se detectó mensaje de error ni página de citas")
            return False

        except Exception as e:
            logger.error(f"Error verificando disponibilidad: {e}")
            return False

    def introducir_dni_busqueda(self) -> bool:
        """Introduce el DNI en el campo de búsqueda de citas."""
        dni = self.config.get('personal', {}).get('dni', '')
        logger.info(f"Introduciendo DNI para búsqueda...")

        if not dni:
            logger.warning("DNI no configurado")
            return False

        try:
            time.sleep(1)

            selectores = [
                (By.ID, "dni"),
                (By.ID, "nif"),
                (By.NAME, "dni"),
                (By.NAME, "nif"),
                (By.CSS_SELECTOR, "input[id*='dni']"),
                (By.CSS_SELECTOR, "input[id*='nif']"),
                (By.CSS_SELECTOR, "input[name*='dni']"),
                (By.CSS_SELECTOR, "input[name*='nif']"),
                (By.CSS_SELECTOR, "input[placeholder*='DNI']"),
                (By.CSS_SELECTOR, "input[placeholder*='NIF']"),
                (By.XPATH, "//input[@type='text']"),
            ]

            for by, value in selectores:
                try:
                    elemento = self.driver.find_element(by, value)
                    if elemento.is_displayed():
                        elemento.clear()
                        elemento.send_keys(dni)
                        logger.info(f"DNI introducido: {dni[:4]}****")
                        time.sleep(1)
                        return True
                except NoSuchElementException:
                    continue
                except Exception:
                    continue

            logger.warning("No se encontró campo para DNI")
            return False

        except Exception as e:
            logger.error(f"Error introduciendo DNI: {e}")
            return False

    def hacer_click_siguiente(self) -> bool:
        """Hace clic en el botón de Siguiente."""
        logger.info("Buscando botón Siguiente...")

        selectores_boton = [
            # Específico para Madrid.es
            (By.XPATH, "//button[text()='Siguiente']"),
            (By.XPATH, "//button[contains(text(), 'Siguiente')]"),
            (By.XPATH, "//input[@value='Siguiente']"),
            # Genéricos
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Continuar')]"),
            (By.XPATH, "//input[@value='Continuar']"),
        ]

        for by, value in selectores_boton:
            if self._wait_and_click(by, value, timeout=5):
                logger.info("Botón Siguiente pulsado")
                time.sleep(2)
                return True

        logger.warning("No se encontró botón de Siguiente")
        return False

    def seleccionar_oficina(self) -> bool:
        """Selecciona la oficina para la cita."""
        oficinas_preferidas = self.config.get('oficinas_preferidas', [])
        logger.info("Buscando oficinas disponibles...")

        try:
            time.sleep(2)

            # Buscar selector de oficinas
            selectores = [
                (By.ID, "oficina"),
                (By.ID, "idOficina"),
                (By.ID, "sede"),
                (By.NAME, "oficina"),
                (By.CSS_SELECTOR, "select[name*='oficina']"),
                (By.CSS_SELECTOR, "select[id*='oficina']"),
                (By.CSS_SELECTOR, "select[name*='sede']"),
            ]

            for by, value in selectores:
                try:
                    select_element = self.wait.until(EC.presence_of_element_located((by, value)))
                    select = Select(select_element)

                    opciones_validas = [opt for opt in select.options if opt.get_attribute('value')]

                    if not opciones_validas:
                        continue

                    # Si hay oficinas preferidas, buscarlas primero
                    if oficinas_preferidas:
                        for preferida in oficinas_preferidas:
                            for option in opciones_validas:
                                if preferida.lower() in option.text.lower():
                                    select.select_by_visible_text(option.text)
                                    logger.info(f"Oficina preferida seleccionada: {option.text}")
                                    time.sleep(1)
                                    return True

                    # Si no hay preferidas o no se encontraron, seleccionar la primera disponible
                    for option in opciones_validas:
                        if option.text.strip() and option.get_attribute('value'):
                            select.select_by_visible_text(option.text)
                            logger.info(f"Oficina seleccionada: {option.text}")
                            time.sleep(1)
                            return True

                except (TimeoutException, NoSuchElementException):
                    continue

            # Buscar como lista de radio buttons o enlaces
            try:
                oficinas = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name*='oficina']")
                if oficinas:
                    self._safe_click(oficinas[0])
                    logger.info("Oficina seleccionada (radio button)")
                    return True
            except Exception:
                pass

            logger.warning("No se encontraron oficinas disponibles")
            return False

        except Exception as e:
            logger.error(f"Error seleccionando oficina: {e}")
            return False

    def buscar_citas_disponibles(self) -> List[dict]:
        """Busca citas disponibles en el calendario."""
        logger.info("Buscando citas disponibles...")
        citas_encontradas = []

        try:
            time.sleep(2)

            # Buscar días disponibles en el calendario
            selectores_dias = [
                "td.disponible a",
                "td.diaDisponible a",
                "a.diaDisponible",
                ".calendario td:not(.noDisponible) a",
                "td[class*='disponible'] a",
                ".fc-day:not(.fc-day-disabled)",
            ]

            for selector in selectores_dias:
                try:
                    dias = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for dia in dias:
                        if dia.is_displayed():
                            citas_encontradas.append({
                                'elemento': dia,
                                'fecha': dia.text or dia.get_attribute('title') or 'Fecha disponible'
                            })
                except Exception:
                    continue

            # Buscar en formato de tabla/lista
            try:
                filas = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
                for fila in filas:
                    if "disponible" in fila.text.lower() or "libre" in fila.text.lower():
                        links = fila.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            citas_encontradas.append({
                                'elemento': link,
                                'fecha': fila.text
                            })
            except Exception:
                pass

            if citas_encontradas:
                logger.info(f"¡Se encontraron {len(citas_encontradas)} citas disponibles!")
            else:
                logger.info("No hay citas disponibles en este momento")

            return citas_encontradas

        except Exception as e:
            logger.error(f"Error buscando citas: {e}")
            return []

    def seleccionar_hora(self) -> bool:
        """Selecciona una hora disponible."""
        horario = self.config.get('horario', {})
        hora_min = horario.get('hora_minima', '00:00')
        hora_max = horario.get('hora_maxima', '23:59')

        logger.info(f"Buscando horas entre {hora_min} y {hora_max}")

        try:
            time.sleep(2)

            # Buscar selector de horas
            selectores = [
                (By.ID, "hora"),
                (By.ID, "idHora"),
                (By.NAME, "hora"),
                (By.CSS_SELECTOR, "select[name*='hora']"),
                (By.CSS_SELECTOR, "select[id*='hora']"),
            ]

            for by, value in selectores:
                try:
                    select_element = self.wait.until(EC.presence_of_element_located((by, value)))
                    select = Select(select_element)

                    for option in select.options:
                        hora_texto = option.text.strip()
                        if ':' in hora_texto:
                            try:
                                hora = hora_texto.split()[0]  # Tomar solo la hora
                                if hora_min <= hora <= hora_max:
                                    select.select_by_visible_text(option.text)
                                    logger.info(f"Hora seleccionada: {option.text}")
                                    return True
                            except Exception:
                                # Si no podemos comparar, seleccionar la primera disponible
                                select.select_by_visible_text(option.text)
                                logger.info(f"Hora seleccionada: {option.text}")
                                return True

                except (TimeoutException, NoSuchElementException):
                    continue

            # Buscar como radio buttons
            try:
                horas = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name*='hora']")
                if horas:
                    self._safe_click(horas[0])
                    logger.info("Hora seleccionada (radio button)")
                    return True
            except Exception:
                pass

            # Buscar como enlaces
            try:
                horas = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'hora') or contains(text(), ':')]")
                for hora in horas:
                    if hora.is_displayed() and ':' in hora.text:
                        self._safe_click(hora)
                        logger.info(f"Hora seleccionada: {hora.text}")
                        return True
            except Exception:
                pass

            logger.warning("No se encontraron horas disponibles")
            return False

        except Exception as e:
            logger.error(f"Error seleccionando hora: {e}")
            return False

    def rellenar_datos_personales(self) -> bool:
        """Rellena el formulario con los datos personales."""
        personal = self.config.get('personal', {})
        logger.info("Rellenando datos personales...")

        campos = {
            'nombre': ['nombre', 'name', 'firstName'],
            'apellidos': ['apellidos', 'apellido', 'surname', 'lastName'],
            'dni': ['dni', 'nif', 'documento', 'docIdentidad'],
            'telefono': ['telefono', 'phone', 'tel', 'movil'],
            'email': ['email', 'correo', 'mail'],
        }

        try:
            time.sleep(2)
            campos_rellenados = 0

            for campo, posibles_ids in campos.items():
                valor = personal.get(campo, '')
                if not valor:
                    continue

                for posible_id in posibles_ids:
                    try:
                        # Buscar por ID
                        elemento = self.driver.find_element(By.ID, posible_id)
                        elemento.clear()
                        elemento.send_keys(valor)
                        campos_rellenados += 1
                        logger.debug(f"Campo {campo} rellenado")
                        break
                    except NoSuchElementException:
                        pass

                    try:
                        # Buscar por NAME
                        elemento = self.driver.find_element(By.NAME, posible_id)
                        elemento.clear()
                        elemento.send_keys(valor)
                        campos_rellenados += 1
                        logger.debug(f"Campo {campo} rellenado")
                        break
                    except NoSuchElementException:
                        pass

                    try:
                        # Buscar por contenido en ID o NAME
                        elemento = self.driver.find_element(
                            By.CSS_SELECTOR,
                            f"input[id*='{posible_id}'], input[name*='{posible_id}']"
                        )
                        elemento.clear()
                        elemento.send_keys(valor)
                        campos_rellenados += 1
                        logger.debug(f"Campo {campo} rellenado")
                        break
                    except NoSuchElementException:
                        continue

            logger.info(f"Datos personales rellenados: {campos_rellenados} campos")
            return campos_rellenados > 0

        except Exception as e:
            logger.error(f"Error rellenando datos personales: {e}")
            return False

    def aceptar_terminos(self) -> bool:
        """Acepta los términos y condiciones si existen."""
        logger.info("Buscando checkboxes de términos...")

        try:
            checkboxes = self.driver.find_elements(
                By.CSS_SELECTOR,
                "input[type='checkbox']"
            )

            for checkbox in checkboxes:
                if not checkbox.is_selected():
                    try:
                        self._safe_click(checkbox)
                        logger.info("Checkbox aceptado")
                    except Exception:
                        pass

            return True

        except Exception as e:
            logger.error(f"Error aceptando términos: {e}")
            return False

    def confirmar_cita(self) -> bool:
        """Confirma la cita."""
        logger.info("Confirmando cita...")

        selectores_confirmar = [
            (By.ID, "confirmar"),
            (By.ID, "btnConfirmar"),
            (By.NAME, "confirmar"),
            (By.XPATH, "//input[@value='Confirmar']"),
            (By.XPATH, "//button[contains(text(), 'Confirmar')]"),
            (By.XPATH, "//input[contains(@value, 'onfirmar')]"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ]

        for by, value in selectores_confirmar:
            if self._wait_and_click(by, value, timeout=5):
                logger.info("Botón confirmar pulsado")
                time.sleep(3)
                return True

        logger.warning("No se encontró botón de confirmar")
        return False

    def verificar_cita_exitosa(self) -> bool:
        """Verifica si la cita se ha confirmado correctamente."""
        try:
            time.sleep(2)
            page_source = self.driver.page_source.lower()

            indicadores_exito = [
                'cita confirmada',
                'reserva realizada',
                'cita reservada',
                'su cita ha sido',
                'confirmación de cita',
                'código de cita',
                'justificante',
            ]

            for indicador in indicadores_exito:
                if indicador in page_source:
                    logger.info(f"¡CITA CONSEGUIDA! Indicador encontrado: {indicador}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error verificando cita: {e}")
            return False

    def capturar_pantalla(self, nombre: str = None) -> str:
        """Captura una pantalla para registro."""
        if not nombre:
            nombre = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        try:
            self.driver.save_screenshot(nombre)
            logger.info(f"Captura guardada: {nombre}")
            return nombre
        except Exception as e:
            logger.error(f"Error capturando pantalla: {e}")
            return ""

    def ejecutar_intento(self) -> bool:
        """Ejecuta un intento completo de obtener cita."""
        try:
            # Paso 1: Navegar a la página
            if not self.navegar_a_pagina_inicial():
                return False

            # Paso 2: Aceptar cookies
            self.aceptar_cookies()

            # Paso 3: Seleccionar acceso sin identificar
            if not self.seleccionar_acceso_sin_identificar():
                logger.warning("No se pudo seleccionar acceso sin identificar")
                # Continuar de todos modos, puede que no sea necesario

            # Paso 4: Seleccionar categoría
            if not self.seleccionar_categoria():
                logger.warning("No se pudo seleccionar la categoría")

            # Paso 5: Seleccionar trámite
            if not self.seleccionar_tramite():
                logger.warning("No se pudo seleccionar el trámite")

            # Paso 6: Clic en "consultar la oficina con cita más temprana"
            self.click_oficina_cita_temprana()

            # Paso 7: Verificar si hay citas disponibles
            if not self.verificar_hay_citas_disponibles():
                logger.info("No hay citas disponibles en este momento")
                return False

            # ¡HAY CITAS DISPONIBLES! Notificar inmediatamente
            logger.info("=" * 50)
            logger.info("¡¡¡ CITAS DISPONIBLES !!!")
            logger.info("=" * 50)

            # Capturar pantalla como evidencia
            screenshot = self.capturar_pantalla("citas_disponibles.png")

            # Notificar al usuario
            mensaje = f"🎉 ¡HAY CITAS DISPONIBLES!\n\nEntra ahora a la web para reservar tu cita.\n\nhttps://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do\n\nCaptura guardada: {screenshot}"
            self._notify(mensaje, is_success=True)

            # Marcar como éxito para detener el bot
            self.cita_conseguida = True
            return True

            # --- El código de abajo se podría usar para reserva automática ---
            # Por ahora solo notificamos que hay citas

            # Paso 8: Introducir DNI (si no se introdujo antes)
            # self.introducir_dni_busqueda()

            # Paso 9: Buscar citas disponibles en calendario
            # citas = self.buscar_citas_disponibles()

            # Paso 10: Seleccionar una cita
            # for cita in citas:
            #     try:
            #         self._safe_click(cita['elemento'])
            #         logger.info(f"Cita seleccionada: {cita['fecha']}")
            #         time.sleep(1)
            #         break
            #     except Exception:
            #         continue

            # Paso 11: Seleccionar hora
            # self.seleccionar_hora()
            # self.hacer_click_siguiente()

            # Paso 12: Rellenar datos personales
            # self.rellenar_datos_personales()

            # Paso 13: Aceptar términos
            self.aceptar_terminos()

            # Paso 14: Confirmar
            self.confirmar_cita()

            # Paso 15: Verificar éxito
            if self.verificar_cita_exitosa():
                self.cita_conseguida = True
                screenshot = self.capturar_pantalla("cita_confirmada.png")
                mensaje = f"🎉 ¡CITA CONSEGUIDA!\n\nCaptura guardada: {screenshot}"
                logger.info(mensaje)
                self._notify(mensaje, is_success=True)
                return True
            else:
                logger.warning("No se pudo confirmar la cita")
                self.capturar_pantalla("intento_fallido.png")
                return False

        except Exception as e:
            logger.error(f"Error durante el intento: {e}")
            self.capturar_pantalla("error.png")
            return False

    def iniciar(self) -> None:
        """Inicia el proceso de búsqueda de citas."""
        logger.info("=" * 50)
        logger.info("Iniciando Bot de Citas - Ayuntamiento de Madrid")
        logger.info("=" * 50)

        self._setup_driver()

        bot_config = self.config.get('bot', {})
        intervalo = bot_config.get('intervalo_comprobacion', 30)
        max_reintentos = bot_config.get('max_reintentos', 100)

        intento = 0

        self._notify("🤖 Bot de citas iniciado. Buscando disponibilidad...")

        try:
            while not self.cita_conseguida and intento < max_reintentos:
                intento += 1
                logger.info(f"\n--- Intento {intento}/{max_reintentos} ---")
                logger.info(f"Hora: {datetime.now().strftime('%H:%M:%S')}")

                if self.ejecutar_intento():
                    break

                if not self.cita_conseguida:
                    logger.info(f"Esperando {intervalo} segundos antes del próximo intento...")
                    time.sleep(intervalo)

            if not self.cita_conseguida:
                mensaje = f"Se alcanzó el límite de {max_reintentos} intentos sin conseguir cita"
                logger.warning(mensaje)
                self._notify(mensaje)

        except KeyboardInterrupt:
            logger.info("\nBot detenido por el usuario")
            self._notify("Bot detenido manualmente")
        finally:
            self.cerrar()

    def cerrar(self) -> None:
        """Cierra el navegador y limpia recursos."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Navegador cerrado")
            except Exception:
                pass
