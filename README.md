# Set up
## Project
WIP, but on linux, it should be:
1. `git clone https://github.com/leoCottret/cambridge-to-anki.git; cd cambridge-to-anki`
1. `pip3 install pipenv`
1. `virtualenv .`
1. `. ./bin/activate`
1. `pip3 install -r requirements.txt`
1. then `deactivate` to leave the virtualenv shell when you're finished
## Anki part
### Optionnal, but better if you want to be able to update your notes
1. Add a Note ID field to all of your cards to all of your cards, so you can update them
    - Tools -> Manage Note Types -> Select Close+ -> Fields -> Add -> Type "Note ID" -> OK -> Reposition -> 1
2. Get an add on to add an ID to all of the cards
- Tools -> Add-ons -> Get Add-ons -> 8897764 -> OK -> Restart Anki
    - PS: source: https://ankiweb.net/shared/info/8897764, the "Add note ID" add-on
3. Use the Add-on
    - Tools -> Add note ids -> yes

    