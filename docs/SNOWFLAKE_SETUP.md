# Snowflake setup, click by click (Person A, tonight)

> **Status (Oct 2):** Parts 1–4 are done. Data lives in `SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE`
> (rent `B25064_001E_5YR`, income `B19013_001E_5YR_<year>`, level `CensusZipCodeTabulationArea`).
> The final query is `sql/02_area_stats.sql`. Next: run it, download the results as CSV, save as
> `data/area_stats_snowflake.csv`. The app uses that snapshot automatically, no login needed.

You'll end with: a free Snowflake account, free Census data in it, CoCo screenshots for the judges, and 4 pieces of info to send back to Claude. Plan on about an hour.

---

## Part 1 · Create your Snowflake account (10 min)

1. Go to **https://signup.snowflake.com**
2. Fill in your name and ASU email, then click **Continue**.
3. On the next screen choose:
   - Edition: **Enterprise**
   - Cloud provider: **AWS**
   - Region: **US West (Oregon)**
   Click **Get started**. Skip the survey questions if offered.
4. Check your email for **"Activate your Snowflake account"** and click the link.
5. Create a **username** and **password**. Write both down; the app needs them later.
6. You're now in **Snowsight** (Snowflake's website). Bookmark this page.

## Part 2 · Turn on CoCo (10 min)

CoCo is Snowflake's AI assistant. On trial accounts it **only works after a credit card is added**. The trial credits still pay for usage, so you shouldn't be charged for a hackathon's worth of queries.

1. Bottom-left corner: click **your name**, then make sure **Switch Role** shows **ACCOUNTADMIN** (click it if not).
2. Add a card: left menu **Admin → Billing** (sometimes called **Billing & Terms**) → **Add payment method**.
3. Turn on AI in any region. Left menu **Projects → Workspaces** (or **Worksheets**) → click **+** to open a new SQL file. Paste this and click the blue **▶ Run** button (top right):
   ```sql
   ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';
   GRANT DATABASE ROLE SNOWFLAKE.COPILOT_USER TO ROLE ACCOUNTADMIN;
   GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ACCOUNTADMIN;
   ALTER USER <your_username> SET DEFAULT_ROLE = ACCOUNTADMIN;
   ```
   Replace `<your_username>` with your username. If a GRANT line says it's already granted, that's fine.
4. **Refresh the page.** Look for the **CoCo icon in the lower-right corner** of Snowsight. Click it; a chat panel opens on the right. Type `hello` to check it works.

## Part 3 · Get the free Census data (10 min)

1. Left menu: **Data Products → Marketplace**.
2. In the search box type **`Snowflake Public Data`** and open the **free** listing with that name (it may say "Free" under the title).
3. Click the blue **Get** button. In the pop-up:
   - Database name: you can leave the default; **write it down**.
   - Roles: select **PUBLIC**.
   - Click **Get**.
4. If that listing doesn't mention "American Community Survey," go back and search **`American Community Survey`** instead, and click **Get** on a free one.
5. Left menu: **Data → Databases**. You should see the new database. Click it to confirm it has tables.

## Part 4 · Explore with CoCo (20 min) 📸 screenshot every answer

Open the CoCo panel (lower-right icon). Paste these one at a time and wait for each answer. **Take a screenshot after each one** (Windows: Win+Shift+S, Mac: Cmd+Shift+4). These screenshots are your proof for the Snowflake category.

1. ```
   Search my available databases for American Community Survey data with median gross rent and median household income by ZIP code or ZCTA.
   ```
2. ```
   In that database, which table and variable hold median gross rent and median household income? Show me the exact variable IDs or names.
   ```
3. ```
   What geography level value is used for ZIP codes / ZCTAs, and how do I join the values table to the geography table?
   ```
4. ```
   Show the median gross rent and median household income for ZIP codes starting with 852 (Tempe, Mesa, Scottsdale, Phoenix area), with the year of the estimate.
   ```
5. ```
   Rewrite that as one query that returns exactly these columns: ZIP, PLACE, MEDIAN_RENT, MEDIAN_INCOME, YEAR, LAT, LON. Use NULL for LAT and LON if there are no coordinates. Only include ZIPs starting with 850, 852, or 853.
   ```
6. Click **Run** (or the run/insert button CoCo shows) on the query from step 5. When it returns rows, check that **85281** is there and the rent looks reasonable.
7. Copy the query from step 5 into a text file and save it.

**If CoCo says there's no ZIP-level rent:** ask *"Is median gross rent available at county or metro (CBSA) level instead?"* and screenshot that answer too. Send it to Claude; the app can compare at county level.

## Part 5 · Find your connection details (5 min)

1. Bottom-left: click **your name → Connect a tool to Snowflake** (or **Account → View account details**).
2. Copy the **Account identifier** (looks like `ABCDEFG-XY12345`).
3. Warehouse name: left menu **Admin → Warehouses**; it's usually **COMPUTE_WH**.

## Part 6 · Send these to Claude

Paste these into the chat (**do not paste your password**):

1. The **database name** (and schema) from Part 3
2. CoCo's answers to Part 4, questions **2 and 3** (variable IDs and geography level)
3. The **query** from Part 4, step 5, plus 2 or 3 result rows, including 85281
4. Your **account identifier** and **warehouse** name

Claude will finish `sql/02_area_stats.sql`. Then you'll put your password into `.streamlit/secrets.toml` yourself (that file never gets uploaded to GitHub).

---

## Part 7 · Connect the app (after Claude updates the query)

1. In the project folder, copy `.streamlit/secrets.toml.example` and rename the copy to `.streamlit/secrets.toml`.
2. Open it in any text editor and fill in account, user, password, warehouse, database, schema.
3. Run `streamlit run app.py`. The bottom of the sidebar should change from **🧪 Mock data** to **❄️ Snowflake · Census ACS**.

## Part 8 · Nearby ZIPs need coordinates (only if the query returns NULL for LAT/LON)

1. Go to **https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html**
2. Click the latest year, then download **ZIP Code Tabulation Areas** (a .zip file).
3. Unzip it and put the `.txt` file in the project folder.
4. Run `python scripts/build_centroids.py 2024_Gaz_zcta_national.txt` (use the actual file name).
