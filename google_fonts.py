import os
import sys
import requests
from requests.exceptions import HTTPError
from jsonschema import validate
import re

api_url = 'https://www.googleapis.com/webfonts/v1/webfonts?key='
api_key = '0123456789abcdef' # get a valid api key at https://developers.google.com/fonts/docs/developer_api

# Selection of desired regex matches (see https://docs.python.org/3/library/re.html#regular-expression-syntax)
# E.g. 'Saira Semi .*', 'regular|italic', '.?serif', etc.
# Put '.*' to match anything
regex_selection = {
	'family':	'.*',		# E.g. 'Saira Semi Condensed', 'Tourney', etc.
	'variants':	'.*',		# E.g. 'regular', 'italic', etc.
	'subsets':	'.*',		# E.g. 'latin', 'vietnamese', etc.
	'category':	'.*',		# E.g. 'display', 'sans-serif', etc.
	'kind':		'.*'		# E.g. 'webfonts', etc.
}

def create_directory(directory: str) -> None:
	print('Directory\n' + ' ' * 4 + 'Name "./{}"'.format(directory))
	if not os.path.exists(directory):
		try:
			os.makedirs(directory)
			print(' ' * 4 + 'Created')
		except Exception as exception:
			print(' ' * 4 + 'Error\n' + ' ' * 8 + 'Unable to create directory\n' + ' ' * 8 + '{}'.format(exception))
			sys.exit('Stopped')
	else:
		print(' ' * 4 + 'Is already present\n' + ' ' * 4 + 'Creation skipped')

def download_catalogue(api_url: str) -> dict:
	print('Catalogue')
	try:
		font_catalogue = requests.get(api_url)
		font_catalogue.raise_for_status()
		print(' ' * 4 + 'Downloaded')
	except HTTPError as exception:
		print(' ' * 4 + 'Error\n' + ' ' * 8 + 'Unable to download\n' + ' ' * 8 + '{}'.format(exception))
		sys.exit('Stopped')

	expected_schema = {
		'$schema': 'http://json-schema.org/draft-04/schema#',
		'type': 'object',
		'properties': {
			'items': {
				'type': 'array',
				'items': [{
					'type': 'object',
					'properties': {
						'family': {'type': 'string'},
						'variants': {'type': 'array', 'items': [{'type': 'string'}]},
						'subsets': {'type': 'array', 'items': [{'type': 'string'}]},
						'files': { 'type': 'object', 'patternProperties': {'^[a-z0-9]+$': {'type': 'string'}}},
						'category': {'type': 'string'},
						'kind': {'type': 'string'}
		  			},
					'required': ['family', 'variants', 'subsets', 'files', 'category', 'kind']
				}],
				'required': ['items']
			}
		}
	}
	try:
		validate(instance = font_catalogue.json(), schema = expected_schema)
		print(' ' * 4 + 'Contains')
		variant_list = []
		subset_list = []
		files_count = 0
		category_list = []
		kind_list = []
		for font in font_catalogue.json()['items']:
			for variant in font['variants']:
				if variant not in variant_list: variant_list.append(variant)
			for subset in font['subsets']:
				if subset not in subset_list: subset_list.append(subset)
			files_count += len(font['files'])
			if font['category'] not in category_list: category_list.append(font['category'])
			if font['kind'] not in kind_list: kind_list.append(font['kind'])
		print(' ' * 8 + '{} different font families'.format(len(font_catalogue.json()['items'])))
		print(' ' * 8 + '{} different font variants'.format(len(variant_list)))
		print(' ' * 8 + '{} different font subsets'.format(len(subset_list)))
		print(' ' * 8 + '{} different font categories'.format(len(category_list)))
		print(' ' * 8 + '{} different font kinds'.format(len(kind_list)))
		print(' ' * 4 + 'Totals {} font files'.format(files_count))
		return font_catalogue.json()['items']
	except Exception as exception:
		print(' ' * 4 + 'Error\n' + ' ' * 8 + 'JSON schema does not match\n' + ' ' * 8 + '{}'.format(exception))
		sys.exit('Stopped')

def select_fonts(font_catalogue: dict, regex_selection: dict) -> list:
	print('Selection')
	print(' ' * 4 + 'Regex criteria')
	for key, value in regex_selection.items():
		print(' ' * 8 + '{}: {}'.format(key.capitalize(), value))

	font_selection = []
	for font in font_catalogue:
		if not re.search(regex_selection['family'], font['family']): continue
		variants = False
		for variant in font['variants']:
			if re.search(regex_selection['variants'], variant): variants = True
		if not variants: continue
		subsets = False
		for subset in font['subsets']:
			if re.search(regex_selection['subsets'], subset): subsets = True
		if not subsets: continue
		if not re.search(regex_selection['category'], font['category']): continue
		if not re.search(regex_selection['kind'], font['kind']): continue
		# we have a match
		for variant, file in font['files'].items():
			if re.search(regex_selection['variants'], variant):
				font_selection.append({'family': font['family'], 'variant': variant, 'file': font['files'][variant]})
	print(' ' * 4 + 'Found {} matching font files'.format(len(font_selection)))
	return font_selection

def download_fonts(api_url: str, font_selection: list, font_directory: str) -> None:
	print('Download')
	font_total = len(font_selection)
	print(' ' * 4 + 'Got {} font files to download'.format(font_total))

	font_counter = 0
	for font in font_selection:
		font_counter += 1
		print(' ' * 4 + 'File {} of {}'.format(font_counter, font_total))
		print(' ' * 8 + 'Family "{}"'.format(font['family']))
		print(' ' * 8 + 'Variant "{}"'.format(font['variant']))
		font_file = './' + font_directory + '/' + font['family'].lower().replace(' ', '_') + '-' + font['variant'].lower() + '.ttf'
		if os.path.isfile(font_file):
			print(' ' * 8 + 'Is already present in file "{}"\n'.format(font_file) + ' ' * 8 + 'Download skipped')
			continue

		try:
			font_content = requests.get(font['file'])
			font_content.raise_for_status()
		except HTTPError as exception:
			print(' ' * 4 + 'Error\n' + ' ' * 8 + 'Unable to download\n' + ' ' * 8 + '{}'.format(exception))
			sys.exit('Stopped')

		try:
			open(font_file, 'wb').write(font_content.content)
			print(' ' * 8 + 'Received {} bytes\n'.format(os.path.getsize(font_file)) + ' ' * 8 + 'Saved to file "{}"'.format(font_file))
		except Exception as exception:
			print(' ' * 8 + 'Error\n' + ' ' * 8 + 'Unable to save to file "{}"\n'.format(font_file) + ' ' * 8 + '{}'.format(exception))
			sys.exit('Stopped')

if __name__ == '__main__':
	font_directory = 'fonts'
	create_directory(font_directory)
	font_catalogue = download_catalogue(api_url + api_key)
	font_selection = select_fonts(font_catalogue, regex_selection)
	download_fonts(api_url + api_key, font_selection, font_directory)
	print('Done')
