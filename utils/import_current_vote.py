from typing import Optional, Callable
import os
import glob


def import_current_vote() -> Optional[Callable]:
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path = os.path.join(os.path.split(dir_path)[0], 'scripts')
    vote_files = glob.glob(os.path.join(dir_path, 'vote_*.py'))
    if len(vote_files) == 0:
        return None
    assert len(vote_files) == 1
    script_name = os.path.splitext(os.path.basename(vote_files[0]))[0]
    name_for_import = 'scripts.' + script_name
    exec(f'from {name_for_import} import start_vote')
    return locals()['start_vote']
