## dbt's `jaffle_shop` + Materialize

If you've used dbt, odds are that you've run across dbt's beloved
[`jaffle_shop`] demo project. `jaffle_shop` allows users to quickly get up and
running with dbt, using some spoofed, static data for a fictional [jaffle shop].

At [Materialize], we specialize in maintaining fast and efficient views over
your streaming data. While we work on hosting a public source of demo streaming
data for analytics, we wanted to provide those familiar with dbt with an easy
way to get up and running with our [dbt-materialize] adapter and
`jaffle_shop`'s data.

We'll show you how easy easy it is to adjust the jaffle shop dbt project to
operate on streaming data. Spoiler alert - we only change our source.

## Getting data into Materialize

### PostgreSQL

We've included a script to generate jaffle shop data for us, we just need
somewhere to point it. In this case, we'll use a PostgreSQL database.

Follow the Materialize [postgres source instructions] to create a PosgtreSQL database
set up with logical replication enabled. heck out our guides for [AWS RDS],
[Azure DB for PostgreSQL], and [Google Cloud SQL].

`bin/setup_pg` contains the scaffolding to create the tables and the publication we
will use for those tables. Run it, making adjustments if needed for your database.

### Materialize

Make sure you have a Materialize account. Log into your account and generate an
[app password]to use in your dbt connection. Keep track of the `Host`, `Password`
and `User` connection parameters. We'll need those later.

`bin/setup_mz` contains the scaffolding to use to create:
    - our Materialize [postgres connection]
    - a jaffle shop specific [cluster] that we will ask to do our translation
      layer computation for us

## Setting up a `jaffle_shop` with Materialize

Setting up the `jaffle_shop` project with Materialize is similar to setting it
up with any other data warehouse. The following instructions are based off the
[traditional `jaffle_shop`] steps with a few Materialize-specific modifications:

1. Follow the first three steps of the `jaffle_shop` instructions: install dbt,
   clone the `jaffle_shop` repository, and navigate to the cloned repo on your
   machine.

1. Install the [dbt-materialize adapter][dbt-materialize]. You may wish to do
   this within a Python virtual environment on your machine:

   ```bash
   python3 -m venv dbt-venv
   source dbt-venv/bin/activate
   pip install dbt-materialize
   ```

1. Create a `jaffle_shop` [dbt profile] that will connect to Materialize. The
   following profile will connect to a Materialize instance running locally on
   your machine. The `host` parameter will need to be updated if it's
   self-hosted in the cloud or run with Docker:

   ```nofmt
    jaffle_shop:
      outputs:
        dev:
          type: materialize
          host: <host>
          port: 6875
          user: <user@domain.com>
          pass: <password>
          database: materialize
          cluster: jaffle_shop
          schema: public
          sslmode: require
      target: dev
   ```

   Note that we've supplied the additional `cluster` parameter to our
   connection, to isolate the work we'll do below.

1. Check that your newly created `jaffle_shop` profile can connect to your
   Materialize instance:

   ```bash
   dbt debug
   ```

1. In your cloned jaffle_shop repository, make the following changes:
    
    - Add a `source/` folder within the models directory to house our source
      creation statment and definition:

    **Filename:** sources/jaffle_shop.sql
    ```
    {{ config(materialized='source') }}

    CREATE SOURCE IF NOT EXISTS {{ this }}
      FROM POSTGRES
      CONNECTION pg_jaffle_shop (PUBLICATION 'mz_jaffle_shop_source')
      FOR TABLES (orders, payments, customers)
      WITH (SIZE = '3xsmall')
    ```

    **Filename:** sources/sources.yml
    ```
    version: 2

    sources:
      - name: jaffle_shop
        schema: '{{ target.schema }}'
        description: Jaffle Shop Postgres Database
        tables:
          - name: orders
          - name: payments
          - name: customers
    ```

    - Update the staging views to use the source you just created, above:

    **Filename:** staging/stg_customers.sql

    ```
    with source as (

        select * from {{ source('jaffle_shop', 'customers') }}

    ),
    ```

    **Filename:** staging/stg_orders.sql
    ```
    with source as (

        select * from {{ source('jaffle_shop', 'orders') }}

    ),
    ```

    **Filename:** staging/stg_payments.sql
    ```
    with source as (

        select * from {{ source('jaffle_shop', 'payments') }}

    ),
    ```

    - In your cloned `dbt_project.yml`, make the following changes to the
     [model materializations]:

   ```yml
    models:
      jaffle_shop:
          materialized: materializedview
          staging:
            materialized: view
   ```

   Here, we are telling materialize to create [views] for our transformation logic,
   and [materialized views] which utilize our `jaffle_shop` compute cluster to 
   join over our data sources, aggregate customer and user information, and write
   it to durable storage for use downstream. These results are incrementally updated
   as data streams into our source.

   - And lastly, rename `models/customers.sql` to `models/dim_customers.sql`, and
   `models/orders.sql` to `models/dim_orders.sql`

   Since we've already created sources with these names, we'll need to be more explicit that our
   transformation materialized views are separate entities than those sources.

   Thats it! 

1. Run the provided models:

   ```bash
   dbt run
   ```

1. In a new shell, connect to Materialize to check out the `jaffle_shop` data
   you just loaded:

   ```bash
   # Connect to Materialize
   psql "postgres://<user>:<password>@<host>:6875/materialize"
   ```

   ```bash
   # Check out your jaffle shop sources!
   materialize=> SHOW SOURCES; 
        name     |   type    |  size   
    -------------+-----------+---------
     customers   | subsource | 3xsmall
     jaffle_shop | postgres  | 3xsmall
     orders      | subsource | 3xsmall
     payments    | subsource | 3xsmall

   # See all the newly created views
   materialize=> SHOW VIEWS;
   # Output:
         name      
    ---------------
     stg_customers
     stg_orders
     stg_payments

   # See only the materialized views
   materialize=> SHOW MATERIALIZED VIEWS;
         name      |   cluster   
    ---------------+-------------
     dim_customers | jaffle_shop
     dim_orders    | jaffle_shop

   # Check out data in one of your core models
    materialize=> select * from dim_customers where customer_lifetime_value != 0 limit 1; 
     customer_id | first_name | last_name |        first_order         |     most_recent_order      | number_of_orders | customer_lifetime_value 
    -------------+------------+-----------+----------------------------+----------------------------+------------------+-------------------------
              14 | Mack       | Rupp      | 2022-10-14 16:34:54.372032 | 2022-10-14 16:54:23.368272 |               13 |                      84
   ```

   To see what else you can do with your data in Materialize, [check out our docs].

1. Test the newly created models:

   ```bash
   dbt test
   ```

1. Generate and view the documentation for your `jaffle_shop` project:
   ```bash
   dbt docs generate
   dbt docs serve
   ```

[postgres source instructions]: https://materialize.com/docs/integrations/cdc-postgres/#direct-postgres-source
[AWS RDS]: https://materialize.com/docs/integrations/aws-rds/
[Azure DB for PostgreSQL]: https://materialize.com/docs/integrations/azure-postgres/
[Google Cloud SQL]: https://materialize.com/docs/integrations/gcp-cloud-sql/
[app password]: https://cloud.materialize.com/access
[cluster]: https://materialize.com/docs/overview/key-concepts/#clusters
[postgres connection]: https://materialize.com/docs/sql/create-connection/#postgres
[source]: https://materialize.com/docs/overview/key-concepts/#sources
[views]: https://materialize.com/docs/overview/key-concepts/#views
[materialized views]: https://materialize.com/docs/overview/key-concepts/#materialized-views
[dbt-materialize]: https://pypi.org/project/dbt-materialize/
[`jaffle_shop`]: https://github.com/dbt-labs/jaffle_shop
[check out our docs]: https://materialize.com/docs/
[dbt profile]: https://docs.getdbt.com/dbt-cli/configure-your-profile
[dbt-materialize plugin]: https://pypi.org/project/dbt-materialize/
[jaffle shop]: https://australianfoodtimeline.com.au/jaffle-craze/
[materialize]: https://materialize.com/
[model materializations]: https://docs.getdbt.com/docs/building-a-dbt-project/building-models/materializations
[our docs]: https://materialize.com/docs/
[traditional `jaffle_shop`]: https://github.com/fishtown-analytics/jaffle_shop
