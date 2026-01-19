#!/bin/bash

# Скрипт для додавання команд в shell

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SHELL_RC="$HOME/.zshrc"

echo "📝 Додаю команди в $SHELL_RC..."

# Перевірка чи вже додано
if grep -q "# Power Schedule aliases" "$SHELL_RC" 2>/dev/null; then
    echo "⚠️  Команди вже додані!"
    echo "Якщо хочеш оновити, видали секцію '# Power Schedule aliases' з $SHELL_RC"
    exit 0
fi

# Додаємо аліаси
cat >> "$SHELL_RC" << EOF

# Power Schedule aliases
alias power-status='cd $SCRIPT_DIR && ./status.sh'
alias power-plan='cd $SCRIPT_DIR && ./plan.sh'
alias power-check='cd $SCRIPT_DIR && ./check_today.sh'
alias power-changes='cd $SCRIPT_DIR && ./changes.sh'
alias power-recommend='cd $SCRIPT_DIR && ./recommend.sh'
EOF

echo "✅ Готово!"
echo ""
echo "Тепер доступні команди:"
echo "  power-status      - вся інформація"
echo "  power-plan        - план на день"
echo "  power-check       - графіки"
echo "  power-changes     - зміни"
echo "  power-recommend   - рекомендація"
echo ""
echo "⚡ Щоб активувати, виконай:"
echo "   source ~/.zshrc"
echo ""
echo "Або просто відкрий новий термінал"
