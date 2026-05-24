from dataclasses import dataclass, field

from bab.models import Card, EnemyIntent, StatusDefinition


@dataclass
class StatusStack:
    id: str
    amount: int


@dataclass
class Combatant:
    id: str
    name: str
    max_hp: int
    hp: int
    block: int = 0
    statuses: dict[str, StatusStack] = field(default_factory=dict)

    intents: list[EnemyIntent] = field(default_factory=list)
    intent_index: int = 0

    def is_alive(self) -> bool:
        return self.hp > 0

    def gain_block(self, amount: int) -> None:
        self.block += amount

    def take_damage(self, amount: int) -> int:
        if amount <= 0:
            return 0

        blocked = min(self.block, amount)
        remaining_damage = amount - blocked

        self.block -= blocked
        self.hp = max(0, self.hp - remaining_damage)

        return remaining_damage

    def lose_hp(self, amount: int) -> int:
        if amount <= 0:
            return 0

        hp_lost = min(self.hp, amount)
        self.hp -= hp_lost

        return hp_lost

    def apply_status(self, status_id: str, amount: int) -> None:
        if amount <= 0:
            return

        if status_id not in self.statuses:
            self.statuses[status_id] = StatusStack(id=status_id, amount=0)

        self.statuses[status_id].amount += amount

    def reduce_status(self, status_id: str, amount: int) -> None:
        if status_id not in self.statuses:
            return

        self.statuses[status_id].amount -= amount

        if self.statuses[status_id].amount <= 0:
            del self.statuses[status_id]

    def get_status_amount(self, status_id: str) -> int:
        if status_id not in self.statuses:
            return 0

        return self.statuses[status_id].amount

    def current_intent(self) -> EnemyIntent | None:
        if not self.intents:
            return None

        return self.intents[self.intent_index % len(self.intents)]

    def advance_intent(self) -> None:
        if not self.intents:
            return

        self.intent_index = (self.intent_index + 1) % len(self.intents)


@dataclass
class CombatState:
    player: Combatant
    enemies: list[Combatant]

    max_energy: int = 3
    energy: int = 3
    turn: int = 1

    draw_pile: list[Card] = field(default_factory=list)
    hand: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)
    exhaust_pile: list[Card] = field(default_factory=list)

    status_database: dict[str, StatusDefinition] = field(default_factory=dict)

    log: list[str] = field(default_factory=list)

    def living_enemies(self) -> list[Combatant]:
        return [enemy for enemy in self.enemies if enemy.is_alive()]

    def first_enemy(self) -> Combatant:
        living_enemies = self.living_enemies()

        if not living_enemies:
            raise ValueError("Combat has no living enemies.")

        return living_enemies[0]

    def reset_energy(self) -> None:
        self.energy = self.max_energy

    def is_victory(self) -> bool:
        return not any(enemy.is_alive() for enemy in self.enemies)

    def is_defeat(self) -> bool:
        return not self.player.is_alive()

    def status_name(self, status_id: str) -> str:
        status_definition = self.status_database.get(status_id)

        if status_definition is not None:
            return status_definition.name

        return status_id.replace("_", " ").title()

    def status_description(self, status_id: str) -> str:
        status_definition = self.status_database.get(status_id)

        if status_definition is not None:
            return status_definition.description

        return "No description available."