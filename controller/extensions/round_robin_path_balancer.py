class RoundRobinPathBalancer:
    def __init__(self):
        self.tracking = {}     # {(src, dst): (next_path_i, [possible_paths])}

    def get_balanced(self, src_id, dst_id, possible_paths):
        key = (src_id, dst_id)
        next_path_i, paths = self.tracking.setdefault(key, (0, possible_paths))
        selected_path = paths[next_path_i]
        self._update_tracking(key)
        return selected_path

    def _update_tracking(self, key):
        used_path_i, possible_paths = self.tracking[key]
        next_path_i = (used_path_i + 1) % len(possible_paths)
        self.tracking[key] = (next_path_i, possible_paths)

    def reset(self):
        self.tracking = {}
