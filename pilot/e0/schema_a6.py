"""Definición de campos del esquema A6 (E0). Fuente única para el parser, la tarjeta del dataset y los tests.

Cada entrada: nombre en el npz -> (ruta en el struct Arrow de peppi o None si es derivado/slpraw, dtype,
unidad, procedencia en SPEC (evento + offset), versión mínima, nivel según timing_contract de A6).
Los campos por puerto se guardan con forma [T, 2] (columna 0 = puerto bajo, 1 = puerto alto).
"""

# ---- por frame (globales) ----
FRAME_FIELDS = {
    "frame_id":            (("id",), "i4", "frame", "Pre/Post 0x1, FrameStart 0x1", "0.1.0", "index"),
    "n_copies":            (None, "u1", "copias", "nº de veces que el frame aparece en el flujo (rollback); derivado", "0.1.0", "training_metadata"),
    "rng_seed":            (("start", "random_seed"), "u4", "estado RNG", "FrameStart 0x5", "2.2.0", "simulator_snapshot"),
    "scene_frame_counter": (("start", "scene_frame_counter"), "u4", "frames", "FrameStart 0x9", "3.10.0", "training_metadata"),
    "latest_finalized":    (("end", "latest_finalized_frame"), "i4", "frame_id", "FrameBookend 0x5", "3.7.0", "training_metadata"),
}

# ---- por puerto: estado post-frame ----
POST_FIELDS = {
    "character":       (("post", "character"), "u1", "id interno", "Post 0x7", "0.1.0", "observation"),
    "action":          (("post", "state"), "u2", "id de action state", "Post 0x8", "0.1.0", "observation"),
    "pos_x":           (("post", "position", "x"), "f4", "unidades de mundo", "Post 0xA", "0.1.0", "observation"),
    "pos_y":           (("post", "position", "y"), "f4", "unidades de mundo", "Post 0xE", "0.1.0", "observation"),
    "facing":          (("post", "direction"), "f4", "signo -1/+1", "Post 0x12", "0.1.0", "observation"),
    "percent":         (("post", "percent"), "f4", "% daño", "Post 0x16", "0.1.0", "observation"),
    "shield":          (("post", "shield"), "f4", "[0,60]", "Post 0x1A", "0.1.0", "observation"),
    "last_attack_landed": (("post", "last_attack_landed"), "u1", "id de ataque", "Post 0x1E", "0.1.0", "observation"),
    "combo_count":     (("post", "combo_count"), "u1", "conteo", "Post 0x1F", "0.1.0", "observation"),
    "last_hit_by":     (("post", "last_hit_by"), "u1", "puerto", "Post 0x20", "0.1.0", "observation"),
    "stocks":          (("post", "stocks"), "u1", "vidas", "Post 0x21", "0.1.0", "observation"),
    "action_frame":    (("post", "state_age"), "f4", "frames en el estado (fraccional)", "Post 0x22", "0.2.0", "observation"),
    "flags1":          (("post", "state_flags", "0"), "u1", "bits", "Post 0x26", "2.0.0", "observation"),
    "flags2":          (("post", "state_flags", "1"), "u1", "bits (0x20 hitlag, 0x08 fastfall)", "Post 0x27", "2.0.0", "observation"),
    "flags3":          (("post", "state_flags", "2"), "u1", "bits (0x80 escudo)", "Post 0x28", "2.0.0", "observation"),
    "flags4":          (("post", "state_flags", "3"), "u1", "bits (0x02 hitstun)", "Post 0x29", "2.0.0", "observation"),
    "flags5":          (("post", "state_flags", "4"), "u1", "bits (0x40 muerto, 0x80 fuera de pantalla)", "Post 0x2A", "2.0.0", "observation"),
    "misc_as":         (("post", "misc_as"), "f4", "multiuso; hitstun restante si flags4&0x02", "Post 0x2B", "2.0.0", "observation"),
    "hitstun_left":    (None, "f4", "frames; = misc_as si flags4&0x02, si no 0 (derivado)", "Post 0x2B + 0x29 bit 0x02", "2.0.0", "observation"),
    "airborne":        (("post", "airborne"), "u1", "0 suelo / 1 aire", "Post 0x2F", "2.0.0", "observation"),
    "ground_id":       (("post", "ground"), "u2", "id de suelo", "Post 0x30", "2.0.0", "observation"),
    "jumps_left":      (("post", "jumps"), "u1", "saltos", "Post 0x32", "2.0.0", "observation"),
    "l_cancel":        (("post", "l_cancel"), "u1", "0/1/2", "Post 0x33", "2.0.0", "observation"),
    "hurtbox":         (("post", "hurtbox_state"), "u1", "0 vuln / 1 invuln / 2 intang", "Post 0x34", "2.1.0", "observation"),
    "vel_air_x_self":  (("post", "velocities", "self_x_air"), "f4", "unidades/frame", "Post 0x35", "3.5.0", "observation"),
    "vel_y_self":      (("post", "velocities", "self_y"), "f4", "unidades/frame", "Post 0x39", "3.5.0", "observation"),
    "vel_x_attack":    (("post", "velocities", "knockback_x"), "f4", "unidades/frame", "Post 0x3D", "3.5.0", "observation"),
    "vel_y_attack":    (("post", "velocities", "knockback_y"), "f4", "unidades/frame", "Post 0x41", "3.5.0", "observation"),
    "vel_ground_x_self": (("post", "velocities", "self_x_ground"), "f4", "unidades/frame", "Post 0x45", "3.5.0", "observation"),
    "hitlag_left":     (("post", "hitlag"), "f4", "frames", "Post 0x49", "3.8.0", "observation"),
    "animation_index": (("post", "animation_index"), "u4", "índice", "Post 0x4D", "3.11.0", "observation"),
}

# ---- por puerto: mandos y estado pre-frame ----
PRE_FIELDS = {
    "pre_rng_seed":   (("pre", "random_seed"), "u4", "estado RNG", "Pre 0x7", "0.1.0", "simulator_snapshot"),
    "pre_action":     (("pre", "state"), "u2", "action state antes del frame", "Pre 0xB", "0.1.0", "training_metadata"),
    "pre_pos_x":      (("pre", "position", "x"), "f4", "unidades de mundo", "Pre 0xD", "0.1.0", "training_metadata"),
    "pre_pos_y":      (("pre", "position", "y"), "f4", "unidades de mundo", "Pre 0x11", "0.1.0", "training_metadata"),
    "pre_facing":     (("pre", "direction"), "f4", "signo", "Pre 0x15", "0.1.0", "training_metadata"),
    "joy_x":          (("pre", "joystick", "x"), "f4", "procesado [-1,1]", "Pre 0x19", "0.1.0", "control"),
    "joy_y":          (("pre", "joystick", "y"), "f4", "procesado [-1,1]", "Pre 0x1D", "0.1.0", "control"),
    "cstick_x":       (("pre", "cstick", "x"), "f4", "procesado [-1,1]", "Pre 0x21", "0.1.0", "control"),
    "cstick_y":       (("pre", "cstick", "y"), "f4", "procesado [-1,1]", "Pre 0x25", "0.1.0", "control"),
    "trigger":        (("pre", "triggers"), "f4", "procesado [0,1]", "Pre 0x29", "0.1.0", "control"),
    "buttons":        (("pre", "buttons"), "u4", "bitmask procesado", "Pre 0x2D", "0.1.0", "control"),
    "buttons_phys":   (("pre", "buttons_physical"), "u2", "bitmask físico (mantenido)", "Pre 0x31", "0.1.0", "control"),
    "trig_l_phys":    (("pre", "triggers_physical", "l"), "f4", "físico [0,1]", "Pre 0x33", "0.1.0", "control"),
    "trig_r_phys":    (("pre", "triggers_physical", "r"), "f4", "físico [0,1]", "Pre 0x37", "0.1.0", "control"),
    "raw_x":          (("pre", "raw_analog_x"), "i1", "crudo UCF", "Pre 0x3B", "1.2.0", "control"),
    "pre_percent":    (("pre", "percent"), "f4", "% daño antes del frame", "Pre 0x3C", "1.4.0", "training_metadata"),
    "raw_y":          (("pre", "raw_analog_y"), "i1", "crudo", "Pre 0x40", "3.15.0", "control"),
    # peppi-py 0.8.6 no expone estos dos: los lee slpraw directamente del flujo
    "raw_cx":         (None, "i1", "crudo C-stick", "Pre 0x41 (slpraw)", "3.17.0", "control"),
    "raw_cy":         (None, "i1", "crudo C-stick", "Pre 0x42 (slpraw)", "3.17.0", "control"),
}

# ---- ítems/proyectiles: formato ragged (solo copia LAST de cada frame) ----
ITEM_FIELDS = {
    "item_row":   (None, "i4", "fila (índice en frame_id) a la que pertenece", "derivado", "3.0.0", "observation"),
    "item_type":  (("type",), "u2", "id de ítem", "Item 0x5", "3.0.0", "observation"),
    "item_state": (("state",), "u1", "estado", "Item 0x7", "3.0.0", "observation"),
    "item_facing": (("direction",), "f4", "signo", "Item 0x8", "3.0.0", "observation"),
    "item_vel_x": (("velocity", "x"), "f4", "unidades/frame", "Item 0xC", "3.0.0", "observation"),
    "item_vel_y": (("velocity", "y"), "f4", "unidades/frame", "Item 0x10", "3.0.0", "observation"),
    "item_pos_x": (("position", "x"), "f4", "unidades de mundo", "Item 0x14", "3.0.0", "observation"),
    "item_pos_y": (("position", "y"), "f4", "unidades de mundo", "Item 0x18", "3.0.0", "observation"),
    "item_damage": (("damage",), "u2", "daño recibido", "Item 0x1C", "3.0.0", "observation"),
    "item_timer": (("timer",), "f4", "frames hasta expirar", "Item 0x1E", "3.0.0", "observation"),
    "item_spawn_id": (("id",), "u4", "spawn id", "Item 0x22", "3.0.0", "observation"),
    "item_owner": (("owner",), "i1", "puerto 0-3 / -1", "Item 0x2A", "3.6.0", "observation"),
}

# Campos que NUNCA pueden entrar en la observación de una política (timing_contract.not_in_observation)
NEVER_IN_OBSERVATION = {"rng_seed", "pre_rng_seed", "latest_finalized", "n_copies", "scene_frame_counter"}

GATE_FIELDS = ["vel_air_x_self", "vel_y_self", "vel_x_attack", "vel_y_attack", "vel_ground_x_self",
               "hitstun_left", "action_frame"]


def all_fields():
    out = {}
    for group, d in (("frame", FRAME_FIELDS), ("post", POST_FIELDS), ("pre", PRE_FIELDS), ("item", ITEM_FIELDS)):
        for k, v in d.items():
            out[k] = dict(group=group, peppi_path=".".join(v[0]) if v[0] else None, dtype=v[1], unit=v[2],
                          spec=v[3], since=v[4], level=v[5])
    return out
