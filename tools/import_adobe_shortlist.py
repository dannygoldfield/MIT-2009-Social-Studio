"""Copy a bounded audition shortlist into this studio, leaving source audio alone."""
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import uuid
from mit2009_studio import server
from mit2009_studio.media import DATA, digest, inspect

SOURCE = Path('/Users/dannygoldfield/Media/Audio/Sound-FX/Adobe')
PICKS = [
    ('Foley/Foley Spring Thick Spring 01.wav', 'Spring surprise', 'Try as punctuation when a prototype suddenly works.'),
    ('Foley/Foley Toy Slinky Movements 01.wav', 'Slinky business', 'Try with a wobbly build or an elastic movement.'),
    ('Foley/Foley Toy Squeak Airy 01.wav', 'Little toy squeak', 'Try on a small reveal or a quick reaction.'),
    ('Foley/Foley Toy Clap Plastic Hands 01.wav', 'Tiny applause', 'Try as a miniature celebration.'),
    ('Foley/Foley Toy Noisemaker Crank Fast 01.wav', 'Crank up the celebration', 'Try with a fast montage or a team victory.'),
    ('Foley/Foley Toy Bee Buzz Low Frequency 01.wav', 'Busy little bee', 'Try with a mechanism coming to life.'),
    ('Foley/Foley Toy Ball Squeaking Above Water One Time 01.wav', 'Squeaky ball', 'Try with a balloon squeeze or a playful close-up.'),
    ('Foley/Foley Toy Hit Drum 01.wav', 'Toy drum punctuation', 'Try to underline a title or a decisive moment.'),
    ('Foley/Foley Toy Spin And Rattle 01.wav', 'Spin and rattle', 'Try on a spinning part or a fast transition.'),
    ('Foley/Foley Tennis Ball  Bounce On Cement 01.wav', 'One little bounce', 'Try as a playful cut between photographs.'),
    ('Industry/Industry Tool Ratchet Movements Short Quick 01.wav', 'Ratchet click', 'Try as a mechanical accent for a build detail.'),
    ('Animals/Animal Mammal Herbivore Guinea Pig Squeak 01.wav', 'Guinea-pig cameo', 'An unexpected candidate for a comic reaction.'),
    ('Human Elements/Human Female Whistle 01.wav', 'Quick whistle', 'Try with a small success or an attention cue.'),
    ('Liquid-Water/Liquid Water Water Blow Bubbles Into Water 05.wav', 'Bubble trouble', 'Try alongside a curious experiment.'),
    ('Liquid-Water/Liquid Water Water Water Balloon Dropped In Water 11.wav', 'Water-balloon plop', 'Try with the balloon challenge or a splashy reveal.'),
]

def main():
    server.initialize()
    rows = server.library()
    # Preserve a local inventory before the first import. Never replace it on reruns.
    backup = DATA / 'before-audio-buckets-library.json'
    if not backup.exists():
        backup.write_text(json.dumps(rows, indent=2) + '\n')
    record_path = DATA / 'adobe-shortlist-provenance.json'
    records = json.loads(record_path.read_text()) if record_path.exists() else []
    added = 0
    for order, (relative, name, suggestion) in enumerate(PICKS, 1):
        source = SOURCE / relative
        checksum = digest(source)
        if any(row.get('sha256') == checksum and row.get('collection') == 'Adobe playful shortlist' for row in rows):
            continue
        identity = uuid.uuid4().hex
        destination = DATA / 'inputs' / f'{identity}.wav'
        shutil.copy2(source, destination)
        assert digest(destination) == checksum
        info = inspect(destination)
        row = dict(id=identity, name=name+'.wav', file=str(destination.relative_to(DATA)),
                   sha256=checksum, created=datetime.now(timezone.utc).isoformat(),
                   role='source', audio_bucket='effect', assessment='unreviewed', notes='',
                   collection='Adobe playful shortlist', shortlist_order=order, suggestion=suggestion,
                   source_filename=source.name, source_provider='Local Adobe sound effects library', **info)
        rows.append(row)
        records.append(dict(id=identity, source=str(source), sha256=checksum, copied_unchanged=True))
        added += 1
    for row in rows:
        if row.get('kind') == 'audio' and row.get('role') == 'source':
            row.setdefault('audio_bucket', {'Bed':'bed','Gesture':'effect','Music':'wildcard'}.get(row.get('ingredient_role'), 'wildcard'))
            row.setdefault('assessment', 'unreviewed')
            row.setdefault('source_filename', row['name'])
            if row['name'].startswith('Music · Suno Stem '):
                row['name'] = row['name'].replace('Music · Suno Stem ', 'Suno wildcard ')
            elif row['name'].startswith('Gesture · '):
                row['name'] = row['name'].replace('Gesture · ', 'Sound effect · ', 1)
            elif row['name'].startswith('Bed · '):
                row['name'] = row['name'].replace('Bed · ', 'Sound bed · ', 1)
    server.save_library(rows)
    record_path.write_text(json.dumps(records, indent=2)+'\n')
    print(f'{added} new Adobe clips copied; {len(records)} total shortlist clips. All await your assessment.')

if __name__ == '__main__':
    main()
