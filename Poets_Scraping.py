from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
from selenium.common.exceptions import StaleElementReferenceException
import undetected_chromedriver as uc
import pandas as pd
import time
import csv
import sys
import numpy as np
import re

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    ver = int(driver.capabilities['chrome']['chromedriverVersion'].split('.')[0])
    driver.quit()
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.page_load_strategy = 'eager'
    # disable location prompts & disable images loading
    prefs = {"profile.default_content_setting_values.geolocation": 2, "profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(version_main = ver, options=chrome_options) 
    driver.set_window_size(1920, 1080)
    driver.maximize_window()
    driver.set_page_load_timeout(300)

    return driver

def scrape_poets(path):

    start = time.time()
    print('-'*75)
    print('Scraping poets.org ...')
    print('-'*75)
    # initialize the web driver
    driver = initialize_bot()

    # initializing the dataframe
    data = pd.DataFrame()

    # if no books links provided then get the links
    if path == '':
        name = 'poets_data.xlsx'
        # getting the books under each category
        links = []
        nbooks, npages = 0, 0
        homepages = ['https://poets.org/teach-poem', 'https://poets.org/lesson-plans']
        for homepage in homepages:
            driver.get(homepage)
            while True:           
                # scraping books urls
                titles = wait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[role='row']")))
                for title in titles:
                    try:
                        nbooks += 1
                        print(f'Scraping the url for poem {nbooks}')
                        link = wait(title, 5).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                        links.append(link)
                    except Exception as err:
                        print('The below error occurred during the scraping from poets.com, retrying ..')
                        print('-'*50)
                        print(err)
                        continue

                # checking the next page
                try:
                    button = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[aria-label='Go to next page']")))
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(2)
                except:
                    break
                    
        # saving the links to a csv file
        print('-'*75)
        print('Exporting links to a csv file ....')
        with open('poets_links.csv', 'w', newline='\n', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Link'])
            for row in links:
                writer.writerow([row])

    scraped = []
    if path != '':
        df_links = pd.read_csv(path)
        name = path.split('\\')[-1][:-4]
        name = name + '_data.xlsx'
    else:
        df_links = pd.read_csv('poets_links.csv')

    links = df_links['Link'].values.tolist()

    try:
        data = pd.read_excel(name)
        scraped = data['Title Link'].values.tolist()
    except:
        pass

    # scraping books details
    print('-'*75)
    print('Scraping poems Info...')
    print('-'*75)
    n = len(links)
    for i, link in enumerate(links):

        if link in scraped: continue
        try:
            driver.get(link)           
            details = {}
            
            try:
                wait(driver, 20, ignored_exceptions=[StaleElementReferenceException]).until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
            except Exception as err:
                try:
                    url = wait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "iframe"))).get_attribute('src')
                    driver.get(url)
                except:
                    print('Frame is not available in the page')
            # title and title link
            title_link, title = '', ''              
            try:
                title_link = link
                try:
                    h1 = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.card-title")))
                    title = h1.get_attribute('textContent').strip()
                except:
                    h1 = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h3.font-serif.py-2")))
                    title = h1.get_attribute('textContent').strip()
                #try:
                #    a = wait(h1, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a")))          
                #    title_link = a.get_attribute('href')
                #except:
                #    title_link = link
            except Exception as err:
                try:     
                    driver.switch_to.default_content()  
                    time.sleep(1)
                    title = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.hero__heading.pb-3"))).get_attribute('textContent').strip()                   
                except:
                    print(f'Warning: failed to scrape the title for poem: {link}')               
                
            
            print(f'Scraping the info for poem {i+1}\{n}')
            details['Title'] = title
            details['Title Link'] = title_link  
            
            # Author and author link
            author, author_link = '', ''
            try:
                span = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.card-subtitle")))
                a = wait(span, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
                author = a.get_attribute('textContent').replace('\n', '').strip().title() 
                author_link = a.get_attribute('href')
            except:
                pass
                    
            details['Author'] = author            
            details['Author Link'] = author_link            

            driver.get(link)

            try:
                driver.switch_to.default_content()
                time.sleep(1)
            except:
                pass

            # submission date
            date = ''
            try:
                date = wait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.sidebar__published"))).get_attribute('textContent').strip() 
            except:
                pass          
                
            details['Submission Date'] = date             
            
            # level
            level = ''
            try:
                divs = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.level__level")))
                for div in divs:
                    level += div.get_attribute('textContent').strip() + ', ' 

                level = level[:-2]
            except:
                pass          
                
            details['Level'] = level              
 
            # type
            type_ = ''
            try:
                type_ = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.type__type"))).get_attribute('textContent').strip() 
            except:
                pass          
                
            details['Type'] = type_            


            # appending the output to the datafame        
            data = data.append([details.copy()])
            # saving data to csv file each 100 links
            if np.mod(i+1, 100) == 0:
                print('Outputting scraped data ...')
                data.to_excel(name, index=False)
        except:
            pass

    # optional output to excel
    data.to_excel(name, index=False)
    elapsed = round((time.time() - start)/60, 2)
    print('-'*75)
    print(f'poets.com scraping process completed successfully! Elapsed time {elapsed} mins')
    print('-'*75)
    driver.quit()

    return data

if __name__ == "__main__":
    
    path = ''
    if len(sys.argv) == 2:
        path = sys.argv[1]
    data = scrape_poets(path)

