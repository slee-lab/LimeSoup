__author__ = "Tiago Botari, Haoyan Huo"
__maintainer__ = "Haoyan Huo"
__email__ = "haoyan.huo@lbl.gov"

import itertools
import re

import bs4

from pprint import pprint

import LimeSoup.parser.tools as tl


class ParserPaper(object):
    def __init__(self, raw_html, parser_type='lxml-xml', debugging=False):
        """
        :param raw_html:
        :param parser_type: can be 'html.parser', 'lxml', 'html5lib', 'lxml-xml'
        :param debugging: True or False
        """
        self.debugging = debugging
        self.soup = bs4.BeautifulSoup(raw_html, parser_type)
        self.parser_type = parser_type
        if debugging:
            self.soup_orig = self.soup

    @staticmethod
    def create_soup(html_xlm, parser_type='html.parser'):
        # parser_types = ['html.parser', 'lxml', 'html5lib', 'lxml-xml']
        return bs4.BeautifulSoup(html_xlm, parser_type)

    def save_soup_to_file(self, filename='soup.html', prettify=True):
        """
        Save the soup to a file to be analysed. This can be used during the
        debugging process.
        :param filename: str that contain the name of the file
        :param prettify: boolean to add spaces on children tags
        :return: None - just save a file on disk
        """
        with open(filename, 'w', encoding='utf-8') as fd_div:
            if prettify:
                fd_div.write(self.soup.prettify())
                fd_div.write('\n')
            else:
                # for item in self.soup:
                #     #fd_div.write(item)
                fd_div.write(str(self.soup))
                fd_div.write('\n')

    def extract_meta(self, *meta_names):
        """
        Extract metadata from <head> section. The <meta> tags will be removed.

        :param meta_names: List of names that should be extracted.
        :return: list of strings.
        """
        results = []
        for name in meta_names:
            for item in self.soup.find_all('meta', attrs={'name': name}):
                if item.has_attr('content'):
                    results.append(item['content'].strip())
                item.extract()
        return results

    def extract_first_meta(self, *meta_names):
        """
        Extract the first metadata from <head> section. The <meta> tag will be removed.

        :param meta_names: List of names that should be extracted.
        :return: a string containing the metadata value.
        """
        for name in meta_names:
            for item in self.soup.find_all('meta', attrs={'name': name}):
                if item.has_attr('content'):
                    value = item['content'].strip()
                    item.extract()
                    return value
        return None

    def get(self, rules):
        results = list()
        for rule in rules:
            finds = self.soup.find_all(**rule)
            for item in finds:
                text = tl.convert_to_text(item.get_text())
                results.append(text)
                item.extract()
        return results

    def get_first_title(self, rules):
        for rule in rules:
            for title_tag in self.soup.find_all(**rule):
                title = tl.convert_to_text(title_tag.get_text())
                title_tag.extract()
                return title

        return None

    def get_keywords(self, rules):
        keywords = []
        for rule in rules:
            for keyword in self.soup.find_all(**rule):
                keywords.append(tl.convert_to_text(keyword.get_text()))
                keyword.extract()

        return keywords

    def remove_tags(self, rules):
        """
        Remove tags from bs4 soup object using a list of bs4 rules to find_all()
        :param rules: list() of dict() of rules of bs4 find_all()
        :return: None
        """
        for rule in rules:
            for s in self.soup.find_all(**rule):
                s.extract()

    def remove_first_tag(self, rules):
        """
        Remove the first found tag from bs4 soup object using
        a list of bs4 rules to find_all() Remove the first tag.
        :param rules: rules: list() of dict() of rules of bs4 find_all()
        :return: None
        """
        for rule in rules:
            for s in self.soup.find_all(limit=1, **rule):
                s.extract()
                return

    def remove_children_based_on_parent(self, parent_rule, child_rule):
        parent_tags = self.soup.find_all(**parent_rule)
        for p_tag in parent_tags:
            child_tags = p_tag.find_all(**child_rule)
            for c_tag in child_tags:
                c_tag.extract()

    def remove_tag_based_on_next_sibling(self, tag_rule, next_sibling_rule):
        next_sibling_tags= self.soup.find_all(**next_sibling_rule)
        for fs_tag in next_sibling_tags:
            if fs_tag.findPrevious().name == tag_rule['name']:
                fs_tag.findPrevious().extract()

    def create_abstract_section(self):
        inside_tags = self.soup.find_all(**{'name': 'section_h1'})
        for tag in inside_tags:
            for t in tag: # the entire article will be included in this tag
                abstract_content = [item for item in itertools.takewhile(
                        lambda t: t == '\n' or t.get('id') not in ['pnlArticleContent'],
                        t.next_siblings)]

                updated_abstract_section = []
                for c in abstract_content:
                    if c != '\n':
                        if c.name == 'h1':
                            c.name = 'h2'
                        updated_abstract_section.append(c)


                section = self.soup.new_tag('section_h2')
                t.wrap(section)
                for c in updated_abstract_section:
                    section.append(c)


    def create_tag_from_selection(self, rule, name_new_tag, name_section=None):
        """
        Create a tag inside a bs4 soup object from a selection using a rule.
        :param rule: a dict() of rules of bs4 find_all()
        :param name_new_tag: new tag's name
        :param name_section: create a <h2> tag with the name_section content
        :return: None
        """
        inside_tags = self.soup.find_all(**rule)
        section = self.soup.new_tag('section_{}'.format(name_new_tag))
        if name_section:
            heading = self.soup.new_tag('h2')
            heading.append(name_section)
            section.append(heading)
        else:
            for s in section.find_all(**{'name': 'h1', 'class': "h--heading3 article-abstract__heading"}):
                s.name = 'h2'
        for tag in inside_tags:
            tag.wrap(section)
            section.append(tag)

    def create_tag_to_paragraphs_inside_tag(self, rule, name_new_tag, name_section=None):
        inside_tags_inter = self.soup.find_all(**rule)
        if len(inside_tags_inter) == 0:
            # self.save_soup_to_file('selction_found_nothing.html')
            # input('Section not created, selection found nothing')
            return 'Section not created, number of paragraphs equal zero.'
        inside_tags = inside_tags_inter[0].find_all(re.compile('(p|ol)|span'), recursive=False)
        # inside_tags = inside_tags_inter[0].find_all('p', recursive=False)
        # inside_tags_ol = inside_tags_inter[0].find_all('ol', recursive=False)
        # inside_tags = inside_tags_p + inside_tags_ol
        if len(inside_tags) == 0:
            # self.save_soup_to_file('selction_found_nothing.html')
            # input('Section not created, number of paragraphs equal zero.')
            return 'Section not created, number of paragraphs equal zero.'
        section = self.soup.new_tag('section_{}'.format(name_new_tag))
        if name_section:
            heading = self.soup.new_tag('h2')
            heading.append(name_section)
            section.append(heading)
        for tag in inside_tags:
            tag_next_sibling = tag
            while True:
                tag_next_sibling = tag_next_sibling.next_sibling
                if tag_next_sibling is None:
                    break
                if tag_next_sibling.name is None:
                    continue
                else:
                    break
            tag.wrap(section)
            section.append(tag)
            if tag_next_sibling is None: break
            if 'section_h' in tag_next_sibling.name:
                break

    def create_tag_sections(self, rule=None):
        """
        Create the standard tags (<section_#>) using a rule to bs4 find_all()
        :param rule:
        :return:
        """
        tag_names = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        for tag_name in tag_names:
            tags = self.soup.find_all(tag_name)  # Tags corresponded to headings
            for each_tag in tags:
                inside_tags = [item for item in itertools.takewhile(
                    lambda t: t.name not in [each_tag.name, 'script'],
                    each_tag.next_siblings)]
                section = self.soup.new_tag('section_{}'.format(tag_name))
                each_tag.wrap(section)
                for tag in inside_tags:
                    section.append(tag)

    def add_child_class_based_on_parent(self, parent_rule, child_rule, child_class):
        parent_tags = self.soup.find_all(**parent_rule)
        for p_tag in parent_tags:
            child_tags = p_tag.find_all(**child_rule)
            for c_tag in child_tags:
                c_tag['class'] = child_class

    def rename_tag(self, rule, new_name='section_h4'):
        tags = self.soup.find_all(**rule)
        for tag in tags:
            tag.name = new_name

    def rename_child_based_on_parent(self, parent_rule, child_rule, new_child_name):
        parent_tags = self.soup.find_all(**parent_rule)
        for p_tag in parent_tags:
            child_tags = p_tag.find_all(**child_rule)
            for c_tag in child_tags:
                c_tag.name = new_child_name

    def strip_tags(self, rules):
        """
        Replace some tag with the children tag.
        :param rules: list of rules for bs4 find_all()
        :return: None
        """
        tags = list()
        for rule in rules:
            for tag in self.soup.find_all(**rule):
                tag.replace_with_children()
                tags.append(tag.name)
        return tags

    def flatten_tags(self, rules):
        """
        Flatten some tags.
        :param rules: list of rules for bs4 find_all()
        :return: None
        """
        for rule in rules:
            for tag in self.soup.find_all(**rule):
                tag.replace_with(' %s ' % tag.get_text())

    def change_name_tag_sections(self):
        tags = self.soup.find_all(re.compile('^h[2-6]'))
        for each_tag in tags:
            each_tag.parent.name = 'section_{}'.format(each_tag.name)

    @property
    def raw_html(self):
        return self.soup.prettify()
