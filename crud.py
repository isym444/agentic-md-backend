from utils.apis import supabase


# CREATE
def create_record(table: str, data: dict):
    return supabase.table(table).insert(data).execute()


# READ ALL
def get_all_records(table: str):
    return supabase.table(table).select("*").execute()


# READ BY ID
def get_record_by_id(table: str, id_field: str, id_value: int):
    return supabase.table(table).select("*").eq(id_field, id_value).single().execute()


# UPDATE
def update_record(table: str, id_field: str, id_value: int, data: dict):
    return supabase.table(table).update(data).eq(id_field, id_value).execute()


# DELETE
def delete_record(table: str, id_field: str, id_value: int):
    return supabase.table(table).delete().eq(id_field, id_value).execute()