import requests
import time
import pandas as pd
from app.config import HASURA_URL, HASURA_HEADERS

def fetch_unparsed_prospects(prospect_id):
    query = """
    query FetchProspects($prospect_id: uuid!) {
      vocallabs_prospects(
        where: {
          prospect_group_id: { _eq: $prospect_id }
        },
        order_by: { created_at: asc }
      ) {
        id
        name
        phone
        data
      }
    }
    """
    variables = {"prospect_id": prospect_id}
    response = requests.post(
        HASURA_URL,
        headers=HASURA_HEADERS,
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame(data["data"]["vocallabs_prospects"])


def update_prospect_name(prospect_id, devanagari_name):
    mutation = """
    mutation UpdateProspect($name: String!, $id: uuid!) {
      update_vocallabs_prospects(
        where: {id: {_eq: $id}}, 
        _set: {name: $name}
      ) {
        affected_rows
      }
    }
    """
    variables = {"name": devanagari_name, "id": prospect_id}

    try:
        response = requests.post(
            HASURA_URL,
            headers=HASURA_HEADERS,
            json={"query": mutation, "variables": variables}
        )
        response.raise_for_status()
        return response.json()["data"]["update_vocallabs_prospects"]["affected_rows"]
    except Exception as e:
        print(f"Error updating {prospect_id}: {e}")
        return 0



def fetch_autostart_campaigns():
    query = """
    {
  vocallabs_campaigns(where: {campaign_lock: {_eq: true}, autostart: {_eq: true}}) {
    id
    client_id
    start_time
    end_time
    active
    campaign_lock
  }
}

    """
    try:
        response = requests.post(
            HASURA_URL,
            headers=HASURA_HEADERS,
            json={"query": query}
        )
        response.raise_for_status()
        data = response.json()
        campaigns = data.get("data", {}).get("vocallabs_campaigns", [])
        if not campaigns:
            return []
        return campaigns
    except Exception as e:
        print(f"Error fetching campaigns: {e}")
        return None

def update_campaign_active_status(campaign_id, active):
    mutation = """
    mutation UpdateCampaignStatus($id: uuid!, $active: Boolean!) {
      update_vocallabs_campaigns_by_pk(pk_columns: {id: $id}, _set: {active: $active}) {
        id
        active
      }
    }
    """
    variables = {
        "id": campaign_id,
        "active": active
    }
    try:
        response = requests.post(
            HASURA_URL,
            headers=HASURA_HEADERS,
            json={"query": mutation, "variables": variables}
        )
        response.raise_for_status()
        return response.json()["data"]["update_vocallabs_campaigns_by_pk"]
    except Exception as e:
        print(f"Error updating campaign {campaign_id}: {e}")
        return None


def fetch_call_and_prompt_data(agent_id: str, call_id: str):
    query = """
    query MyQuery($agent_id: uuid, $call_id: uuid) {
      vocallabs_agent(where: {id: {_eq: $agent_id}}) {
        agent_post_data_collections { key prompt }
      }
      vocallabs_calls(where: {id: {_eq: $call_id}, call_status: {_eq: "completed"}}) {
        post_call_transcript
        call_messages { 
          role 
          content 
        }
      }
    }
    """
    variables = {"agent_id": agent_id, "call_id": call_id}

    try:
        print("📡 Sending request to Hasura...")
        start_time = time.time()

        response = requests.post(
            HASURA_URL,
            json={"query": query, "variables": variables},
            headers=HASURA_HEADERS,
            timeout=10  # ⏱️ force fail if >10s
        )

        duration = time.time() - start_time
        print(f"✅ Hasura responded in {duration:.2f} seconds")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        print("⏰ Timeout when calling Hasura")
        raise

    except requests.exceptions.RequestException as e:
        print(f"❌ Hasura error: {e}")
        raise


def insert_call_data(key: str, value: str, call_id: str, data_type: str = "external"):
    mutation = """
    mutation MyMutation($key: String!, $value: String!, $call_id: uuid!, $type: String!) {
      insert_vocallabs_call_data(
        objects: {key: $key, value: $value, call_id: $call_id, type: $type},
      
        on_conflict: {constraint: call_data_call_id_key_key, update_columns: value}
      ) {
        affected_rows
      }
    }
    """
    variables = {
        "key": key,
        "value": value,
        "call_id": call_id,
        "type": data_type
    }
    response = requests.post(
        HASURA_URL,
        json={"query": mutation, "variables": variables},
        headers=HASURA_HEADERS
    )
    response.raise_for_status()
    return response.json()
