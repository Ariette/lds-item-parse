import requests
import re
import concurrent.futures
import lxml.html as lxml
import json
import multiprocessing
import time

list_base_url = 'https://na.finalfantasyxiv.com/lodestone/playguide/db/item/?page='
item_base_url = 'https://na.finalfantasyxiv.com/lodestone/playguide/db/item/'
max_page_id = 0

list_page_url_regex = r'<li class=\"current\"><a href=\"https://na\.finalfantasyxiv\.com/lodestone/playguide/db/item/\?page=(\d+)\">'
list_page_item_url_regex = r'<a href=\"\/lodestone\/playguide\/db\/item\/([a-f0-9]{11})\/\">'
item_content_regex = re.compile(r'.*<div class=\"db_cnts\">(.*?)<a name=\"comment\">.*', re.DOTALL)

# find highest pageid
page = requests.get('%s%i' % (list_base_url, 100000))
if page.status_code == 200:
    m = re.search(list_page_url_regex, page.text)
    max_page_id = int(m.group(1))
    print("found max page id:", max_page_id)


def chunker(seq, size):
    return (seq[i::size] for i in range(size))


def process_item(parsed_items, lds_id):
    try:
        html = requests.get("%s%s/" % (item_base_url, lds_id)).text

    except:
        try:
            print('Retry ' + "%s%s/" % (item_base_url, lds_id))
            html = requests.get("%s%s/" % (item_base_url, lds_id)).text

        except:
            try:
                print('Retry Again ' + "%s%s/" % (item_base_url, lds_id))
                html = requests.get("%s%s/" % (item_base_url, lds_id)).text

            except:
                print('Faild to process : ' + "%s%s/" % (item_base_url, lds_id))
                return

    item_html = '<div><div class="db_cnts">' + re.match(item_content_regex, html).group(1)
    item_page = lxml.fromstring(item_html)
    item_name = str(item_page.xpath("//h2[contains(@class,'db-view__item__text__name')]/text()")[0]).strip().replace("\ue03c", "")

    # class = db__l_main db__l_main__view
    item_acquire_list = item_page.xpath("//div[@class='db-view__data__inner--select_reward']")
    if len(item_acquire_list):
        title = item_acquire_list[0].xpath(".//h4")[0].text_content().strip()
        if title == 'Acquired From':
            item_acquire_list = item_acquire_list[0].xpath(".//li[contains(@class,'db-view__data__item_list')]")
            item_acquires = []
            for acquire in item_acquire_list:
                acquire_name = acquire.xpath(".//div[@class='db-view__data__reward__item__name']")[0].text_content().strip()
                item_acquires.append(acquire_name)

    # class= db__l_main db__l_main__base
    item_base_list = item_page.xpath("//div[contains(@class,'db__l_main db__l_main__base')]")
    for base in item_base_list:
        title = base.xpath(".//h3")[0].text_content().strip()
        if title == 'Dropped By':
            item_mob_list = base.xpath(".//tbody/tr")
            item_mobs = []
            for mob in item_mob_list:
                mob_name = mob.xpath(".//td[contains(@class,'db-table__body--light')]/a[contains(@class,'db-table__txt--detail_link')]")[0].text_content().strip()
                item_mobs.append(mob_name)
        if title == 'Related Duties':
            item_instance_list = base.xpath(".//tbody/tr")
            item_instances = []
            for instance in item_instance_list:
                instance_name = instance.xpath(".//td[contains(@class,'db-table__body--light')]/a[contains(@class,'db-table__txt--detail_link')]")[0].text_content().strip()
                item_instances.append(instance_name)

    item_data = {}
    if 'item_acquires' in locals():
        item_data['Acquire'] = item_acquires
    if 'item_mobs' in locals():
        item_data['Drop'] = item_mobs
    if 'item_instances' in locals():
        item_data['Instance'] = item_instances
    parsed_items[lds_id] = {item_name: item_data}


def start_process(parsed_items, ary):
    for idx in ary:
        url = "%s%i" % (list_base_url, idx)
        list_page = requests.get(url).text
        print("Processing page", idx, "of", max_page_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as exec:
            for lds_id in re.findall(list_page_item_url_regex, list_page):
                if lds_id not in parsed_items.keys():
                    exec.submit(process_item, parsed_items, lds_id)


if __name__ == '__main__':
    start_time = time.time()

    try:
        with open('lodestone-data.json', 'r', encoding='utf-8') as k:
            load_data = json.load(k)
            print("Successfully loaded. Continue with previous data...")
    except:
        load_data = {}
        print("Can't load saved data. Initializing steps...")

    pool = multiprocessing.Pool(processes=2)
    manager = multiprocessing.Manager()
    parsed_items = manager.dict(load_data)
    pages = list(chunker(range(1, max_page_id + 1), 8))

    pool.starmap(start_process, [(parsed_items, ary) for ary in pages])
    pool.close()
    pool.join()

    print("--- %s seconds spent ---" % (time.time() - start_time))
    with open('lodestone-data.json', 'w+') as f:
        json_str = json.dump(parsed_items.copy(), f)

    print("Processing data to GarlandTools Supplemental Data")
    tsv_str = 'Item	Category	Sources'
    for ids, item in parsed_items.items():
        for name, source in item.items():
            for category, value in source.items():
                tsv_str = tsv_str + '\n' + name + '	' + category + '	' + '	'.join(value)

    with open('FFXIV Data - Items.tsv', 'w+') as k:
        k.write(tsv_str)

    print("All done.")