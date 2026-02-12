#!/usr/bin/env python3
"""
Bot de Citas Automáticas - Ayuntamiento de Madrid

Este script automatiza la obtención de citas para trámites de Padrón
y otros servicios del Ayuntamiento de Madrid.

Uso:
    python main.py                  # Ejecutar con config.yaml
    python main.py --config mi.yaml # Usar archivo de config personalizado
    python main.py --test           # Probar notificaciones
    python main.py --headless       # Ejecutar sin ventana visible
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from colorama import init, Fore, Style

from src.bot import MadridAppointmentBot
from src.notifier import Notifier, SoundNotifier

# Inicializar colorama para colores en terminal
init()


def setup_logging(verbose: bool = False) -> None:
    """Configura el sistema de logging."""
    level = logging.DEBUG if verbose else logging.INFO

    # Formato con colores
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': Fore.CYAN,
            'INFO': Fore.GREEN,
            'WARNING': Fore.YELLOW,
            'ERROR': Fore.RED,
            'CRITICAL': Fore.RED + Style.BRIGHT,
        }

        def format(self, record):
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
            record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
            return super().format(record)

    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    ))

    logging.basicConfig(
        level=level,
        handlers=[handler]
    )


def load_config(config_path: str) -> dict:
    """Carga la configuración desde un archivo YAML."""
    path = Path(config_path)

    if not path.exists():
        print(f"{Fore.RED}Error: No se encontró el archivo de configuración: {config_path}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}Crea un archivo config.yaml basándote en config.example.yaml:{Style.RESET_ALL}")
        print(f"  cp config.example.yaml config.yaml")
        print(f"  # Edita config.yaml con tus datos")
        sys.exit(1)

    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def validate_config(config: dict) -> bool:
    """Valida que la configuración tenga los campos necesarios."""
    required = ['personal', 'tramite']

    for field in required:
        if field not in config:
            print(f"{Fore.RED}Error: Falta el campo '{field}' en la configuración{Style.RESET_ALL}")
            return False

    personal = config.get('personal', {})
    required_personal = ['nombre', 'apellidos', 'dni', 'telefono', 'email']

    for field in required_personal:
        if not personal.get(field):
            print(f"{Fore.YELLOW}Advertencia: Campo '{field}' vacío en datos personales{Style.RESET_ALL}")

    return True


def print_banner():
    """Muestra el banner del programa."""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   {Fore.WHITE}🏛️  BOT DE CITAS - AYUNTAMIENTO DE MADRID  🏛️{Fore.CYAN}              ║
║                                                              ║
║   {Fore.YELLOW}Automatiza la obtención de citas para el Padrón{Fore.CYAN}           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Bot de Citas Automáticas - Ayuntamiento de Madrid'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Archivo de configuración (default: config.yaml)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Mostrar mensajes de debug'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Ejecutar sin ventana visible'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Probar las notificaciones'
    )
    parser.add_argument(
        '--intervalo',
        type=int,
        help='Intervalo entre comprobaciones (segundos)'
    )

    args = parser.parse_args()

    print_banner()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)

    # Cargar configuración
    config = load_config(args.config)

    if not validate_config(config):
        sys.exit(1)

    # Aplicar argumentos de línea de comandos
    if args.headless:
        config.setdefault('bot', {})['headless'] = True

    if args.intervalo:
        config.setdefault('bot', {})['intervalo_comprobacion'] = args.intervalo

    # Configurar notificador
    notifier = Notifier(config)

    # Modo test: probar notificaciones
    if args.test:
        print(f"\n{Fore.CYAN}Probando notificaciones...{Style.RESET_ALL}\n")
        results = notifier.test_notifications()

        for channel, success in results.items():
            if success is None:
                print(f"  {channel}: {Fore.YELLOW}No configurado{Style.RESET_ALL}")
            elif success:
                print(f"  {channel}: {Fore.GREEN}OK{Style.RESET_ALL}")
            else:
                print(f"  {channel}: {Fore.RED}Error{Style.RESET_ALL}")

        print(f"\n{Fore.CYAN}Probando sonido...{Style.RESET_ALL}")
        SoundNotifier.beep(2)
        print(f"  Sonido: {Fore.GREEN}Enviado{Style.RESET_ALL}")

        sys.exit(0)

    # Mostrar configuración
    print(f"\n{Fore.CYAN}Configuración:{Style.RESET_ALL}")
    print(f"  Categoría: {config.get('tramite', {}).get('categoria', 'No especificada')}")
    print(f"  Trámite: {config.get('tramite', {}).get('nombre', 'No especificado')}")
    print(f"  Intervalo: {config.get('bot', {}).get('intervalo_comprobacion', 30)}s")
    print(f"  Headless: {'Sí' if config.get('bot', {}).get('headless', False) else 'No'}")

    telegram_enabled = config.get('telegram', {}).get('enabled', False)
    email_enabled = config.get('email', {}).get('enabled', False)
    print(f"  Telegram: {'Activo' if telegram_enabled else 'Desactivado'}")
    print(f"  Email: {'Activo' if email_enabled else 'Desactivado'}")

    print(f"\n{Fore.YELLOW}Presiona Ctrl+C para detener el bot{Style.RESET_ALL}\n")

    # Crear y ejecutar el bot
    bot = MadridAppointmentBot(config, notifier.send)

    try:
        bot.iniciar()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot detenido por el usuario{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        # Notificar error
        notifier.send(f"❌ Error en el bot: {str(e)}")
        raise
    finally:
        bot.cerrar()

    # Si se consiguió cita, emitir sonido
    if bot.cita_conseguida:
        print(f"\n{Fore.GREEN}{'='*50}")
        print(f"  🎉 ¡CITA CONSEGUIDA CON ÉXITO!")
        print(f"{'='*50}{Style.RESET_ALL}\n")
        SoundNotifier.beep(5)


if __name__ == '__main__':
    main()
