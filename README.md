## Server setup

1. Setup venv: `python3 -m venv venv`
2. Activate: `source venv/bin/activate`
3. Install requirements: `pip install -r requirements.txt`
4. Copy `config.example.py` to `config.py` and fill out the values

## Frontend setup

1. `cd svelte`
2. `npm install`
3. Create production build: `npm run build`. Output is in `svelte/public`

## Dev

- Dev server: `FLASK_ENV=development flask run`
- Svelte dev: `cd svelte; npm run dev`

## License

All the code in this repository is in the public domain. Or if you prefer, you may also use it under the [MIT license](LICENSE-MIT) or [CC0 license](LICENSE-CC0).

