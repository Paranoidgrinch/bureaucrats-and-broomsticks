# Adding New Effect Types

New effect types should be rare and deliberate.

Most new content should reuse existing effect types.

For a new card or enemy effect:
1. Add the effect literal in src/bab/models/types.py.
2. Add a handler in src/bab/rules/card_effect_handlers.py.
3. Add tests in tests/rules/.
4. Add JSON content using the new effect type.

For a new relic effect:
1. Add the effect literal in src/bab/models/types.py.
2. Add a handler in src/bab/rules/relic_effect_handlers.py.
3. Add tests in tests/rules/.
4. Add JSON content using the new effect type.

For a new event effect:
1. Add the effect literal in src/bab/models/types.py.
2. Add a handler in src/bab/console/event_effect_handlers.py.
3. Add tests in tests/rules/.
4. Add JSON content using the new effect type.
