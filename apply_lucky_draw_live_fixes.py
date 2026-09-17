from pathlib import Path

path = Path("guest_management/state/lucky_draw_state.py")
text = path.read_text(encoding="utf-8")
changes = []

needle = '    lucky_draw_current_id: str = ""\n    lucky_draw_winner: Dict[str, Any] = {}\n'
insert = (
    '    lucky_draw_current_id: str = ""\n'
    '    lucky_draw_winner: Dict[str, Any] = {}\n\n'
    '    # Presentation-only names shown while the wheel is spinning.\n'
    '    wheel_names: List[str] = []\n'
)
if needle in text and "wheel_names: List[str]" not in text:
    text = text.replace(needle, insert, 1)
    changes.append("added wheel_names state")

needle = '        self.lucky_draw_current_id = ""\n\n        self.waiting_for_next_prize = False\n'
if needle in text and '        self.wheel_names = []\n' not in text:
    text = text.replace(
        needle,
        '        self.lucky_draw_current_id = ""\n'
        '        self.wheel_names = []\n\n'
        '        self.waiting_for_next_prize = False\n',
        1,
    )
    changes.append("clear wheel_names on reset")

idx = text.find('    async def start_lucky_draw(self):')
if idx < 0:
    raise SystemExit("start_lucky_draw() not found")
endidx = text.find('    async def _select_candidate(self):', idx)
if endidx < 0:
    raise SystemExit("_select_candidate() not found")
block = text[idx:endidx]

old = (
    '        if not self.current_prizes:\n'
    '            yield rx.toast.error(\n'
    '                "No prizes configured."\n'
    '            )\n'
    '            return\n'
)
new = (
    '        # Normalize any supported prize upload source into current_prizes.\n'
    '        if not self.current_prizes:\n'
    '            source = (\n'
    '                self.prize_list\n'
    '                or self.multiple_prizes_list\n'
    '                or self.excel_prizes_list\n'
    '            )\n'
    '            self.current_prizes = [\n'
    '                dict(prize)\n'
    '                for prize in (source or [])\n'
    '                if isinstance(prize, dict)\n'
    '                and str(prize.get("name") or "").strip()\n'
    '            ]\n'
    '            if self.current_prizes:\n'
    '                self.current_prize_index = max(\n'
    '                    0,\n'
    '                    min(self.current_prize_index, len(self.current_prizes) - 1),\n'
    '                )\n'
    '                self._set_current_prize()\n\n'
    '        if not self.current_prizes:\n'
    '            yield rx.toast.error(\n'
    '                "No prizes configured. Please configure at least one prize."\n'
    '            )\n'
    '            return\n'
)
if old in block:
    block = block.replace(old, new, 1)
    changes.append("normalize prize upload sources")

needle = (
    '            if not candidates:\n'
    '                raise RuntimeError(\n'
    '                    "No eligible candidates remain."\n'
    '                )\n\n'
    '            # Run a short, visually engaging name-roll animation.\n'
)
replacement = (
    '            if not candidates:\n'
    '                raise RuntimeError(\n'
    '                    "No eligible candidates remain."\n'
    '                )\n\n'
    '            # Presentation-only names. Final winner selection remains backend authoritative.\n'
    '            shuffled = list(candidates)\n'
    '            random.shuffle(shuffled)\n'
    '            self.wheel_names = [\n'
    '                str(guest.get("name") or "Guest")\n'
    '                for guest in shuffled[:min(12, len(shuffled))]\n'
    '            ]\n\n'
    '            # Deliberately longer visual roll for a live audience.\n'
)
if needle in block and 'self.wheel_names = [' not in block:
    block = block.replace(needle, replacement, 1)
    changes.append("populate random wheel names")

old_anim = (
    '            animation_count = min(\n'
    '                30,\n'
    '                max(12, len(candidates)),\n'
    '            )\n'
)
new_anim = (
    '            animation_count = min(\n'
    '                52,\n'
    '                max(32, len(candidates) * 2),\n'
    '            )\n'
)
if old_anim in block:
    block = block.replace(old_anim, new_anim, 1)
    changes.append("lengthen name roll")

old_delay = (
    '                progress = step / max(1, animation_count - 1)\n'
    '                delay = 0.04 + (0.20 * (progress ** 2))\n'
    '                await asyncio.sleep(delay)\n'
)
new_delay = (
    '                progress = step / max(1, animation_count - 1)\n'
    '                delay = 0.045 + (0.18 * (progress ** 2))\n'
    '                await asyncio.sleep(delay)\n'
)
if old_delay in block:
    block = block.replace(old_delay, new_delay, 1)
    changes.append("adjust roll timing")

text = text[:idx] + block + text[endidx:]

idx = text.find('    async def proceed_to_next_prize(self):')
if idx < 0:
    raise SystemExit("proceed_to_next_prize() not found")
endidx = text.find('    async def start_lucky_draw(self):', idx)
block = text[idx:endidx]

old_lock = (
    '        if self.draw_locked:\n'
    '            yield rx.toast.warning(\n'
    '                "The draw is currently locked."\n'
    '            )\n'
    '            return\n\n'
    '        if self.draw_status != "CONFIRMED":\n'
)
new_lock = (
    '        # CONFIRMED is the safe boundary for this transition. An active\n'
    '        # draw cannot legitimately be CONFIRMED, so a stale UI lock must\n'
    '        # not block the operator from moving to the next prize.\n'
    '        if self.draw_status != "CONFIRMED":\n'
)
if old_lock in block:
    block = block.replace(old_lock, new_lock, 1)
    changes.append("remove stale lock blocking next prize")

text = text[:idx] + block + text[endidx:]
path.write_text(text, encoding="utf-8")

print("Applied:", changes)
if not changes:
    raise SystemExit("No changes applied; current state file differs from expected structure.")
