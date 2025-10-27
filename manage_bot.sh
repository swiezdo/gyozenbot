#!/bin/bash
# Скрипт для управления Gyozen Telegram Bot

case "$1" in
    start)
        echo "🤖 Запуск Gyozen Bot..."
        systemctl start gyozenbot
        ;;
    stop)
        echo "🛑 Остановка Gyozen Bot..."
        systemctl stop gyozenbot
        ;;
    restart)
        echo "🔄 Перезапуск Gyozen Bot..."
        systemctl restart gyozenbot
        ;;
    status)
        echo "📊 Статус Gyozen Bot:"
        systemctl status gyozenbot --no-pager
        ;;
    logs)
        echo "📝 Логи Gyozen Bot (Ctrl+C для выхода):"
        journalctl -u gyozenbot -f
        ;;
    enable)
        echo "✅ Включение автозапуска Gyozen Bot..."
        systemctl enable gyozenbot
        ;;
    disable)
        echo "❌ Отключение автозапуска Gyozen Bot..."
        systemctl disable gyozenbot
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "Команды:"
        echo "  start    - Запустить бота"
        echo "  stop     - Остановить бота"
        echo "  restart  - Перезапустить бота"
        echo "  status   - Показать статус"
        echo "  logs     - Показать логи в реальном времени"
        echo "  enable   - Включить автозапуск"
        echo "  disable  - Отключить автозапуск"
        exit 1
        ;;
esac

