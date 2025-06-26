from fastapi import APIRouter, HTTPException,Header,Depends
from app.services.openrouter import convert_prospect_language
from app.schemas.request import ProspectRequest,HeaderModel,PostcallRequest
from app.services.hasura import (
    fetch_unparsed_prospects, 
    update_prospect_name,fetch_autostart_campaigns,
     update_campaign_active_status,
     insert_multiple_call_data,
     get_agent_prompt_and_count, 
     get_calls_by_batch

)
from concurrent.futures import ThreadPoolExecutor,as_completed
import time
from app.services.auth import check_auth
from app.services.helper import determine_campaign_status
from functools import partial
from app.services.openrouter import evaluate_prompt


router=APIRouter() 
def get_headers(
    authorization: str = Header(..., alias="Authorization"),
    content_type: str = Header(..., alias="Content-Type")
):
    return {
        "Authorization": authorization,
        "Content-Type": content_type
    }

@router.post("/process-prospects", include_in_schema=True)
async def process_prospects(body: ProspectRequest, headers: dict = Depends(get_headers)):

    hasura_auth_data = await check_auth(body, headers)

    try:
        df = fetch_unparsed_prospects(body.input.prospect_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prospect: {e}")

    if df.empty:
        return {"message": "No prospects found."}

    language = body.input.language  # <-- Get language from request body
    batch_size = 100
    results = []

    # Apply language to convert_to_devanagari using partial
    convert_func = partial(convert_prospect_language, language=language)

    for i in range(0, len(df), batch_size):
        batch = df['name'][i:i+batch_size].tolist()
        with ThreadPoolExecutor(max_workers=15) as executor:
            batch_results = list(executor.map(convert_func, batch))
        results.extend(batch_results)
        time.sleep(1)

    df['converted_name'] = results

    final_results = []
    for _, row in df.iterrows():
        final_results.append({
            "id": row['id'],
            "name": row['converted_name'] or row['name'],
            "phone": row['phone'],
            "data": row['data']
        })

    success_count = 0
    for i in range(0, len(final_results), batch_size):
        batch = final_results[i:i+batch_size]
        with ThreadPoolExecutor(max_workers=10) as executor:
            batch_updates = list(executor.map(lambda x: update_prospect_name(x['id'], x['name']), batch))
        success_count += sum(batch_updates)
        time.sleep(1)

    return {
        "message": f"Processed and updated {success_count}/{len(final_results)} prospects.",
        "success_count": success_count,
        "auth": hasura_auth_data
    }



@router.post("/toggle-campaigns")
def toggle_campaigns():
    try:
        campaigns = fetch_autostart_campaigns()
        
        if campaigns is None:
            return {"success": False, "message": "Failed to fetch campaigns due to an internal error."}
        
        if not campaigns:
            return {"success": True, "message": "No campaigns with autostart found."}
        activated=0
        deactivated=0
        results = []
        for campaign in campaigns:
            try:
                new_status = determine_campaign_status(campaign["start_time"], campaign["end_time"])
                if new_status is not None and campaign["active"] != new_status:
                    update_result = update_campaign_active_status(campaign["id"], new_status)
                    if update_result is not None:
                        results.append(update_result)
                        if new_status:
                           activated += 1
                        else:
                           deactivated += 1
                    else:
                        print(f"Failed to update campaign {campaign['id']}")
            except Exception as e:
                print(f"Error while processing campaign {campaign['id']}: {e}")
                continue

        return {
            "success": True,
            "message": f"{len(results)} campaign(s) updated.",
            "updated_campaigns": results,
            "activated_campaigns": activated,
            "deactivated_campaigns": deactivated
        }

    except Exception as e:
        print(f"Critical error in toggle_campaigns: {e}")
        return {"success": False, "message": "Unexpected server error occurred."}


@router.post("/PCA-batching")
async def admin_vocallabs(body: PostcallRequest):
    start_total = time.time()
    agent_id = body.input.agent_id
    is_premium = body.input.is_premium
    _gte = body.input.from_date
    _lte = body.input.to_date

    print(f"📡 Fetching agent prompt templates and call count...")
    agent_data = get_agent_prompt_and_count(agent_id)
    total_calls = agent_data["calls_aggregate"]["aggregate"]["count"]
    prompts = agent_data["agent_post_data_collections"]

    if total_calls == 0:
        raise HTTPException(status_code=404, detail="No completed calls found")

    print(f"📞 Total calls: {total_calls} | 🧠 Prompts per call: {len(prompts)}")

    batch_size = 100
    loop_count = math.ceil(total_calls / batch_size)
    print(f"🔁 {loop_count} batches of {batch_size} calls each")

    def process_batch(offset: int) -> int:
        print(f"\n🚀 Processing batch at offset {offset}")
        calls = get_calls_by_batch(agent_id, _gte, _lte, offset, batch_size, is_premium)
        batch_results: List[Dict] = []

        for call in calls:
            call_id = call["call_id"]
            transcript = call.get("post_call_transcript")
            messages = call.get("call_messages")

            if not transcript and not messages:
                print(f"⚠️ Skipping call {call_id} — no transcript or messages.")
                continue

            if not is_premium:
                transcript = "\n".join([f"{msg['role']}: {msg['content'].strip()}" for msg in messages])

            print(f"📞 Call {call_id} — {len(prompts)} prompt(s)")

            for item in prompts:
                full_prompt = f"{item['prompt']}\n\n\nChat Transcript:\n{transcript}\n\n\n"
                print(f"🔍 key: {item['key']} | Prompt size: {len(full_prompt)} chars")

                llm_start = time.time()
                result = evaluate_prompt(full_prompt)
                print(f"🧠 LLM took {time.time() - llm_start:.2f}s → result: {result}")

                batch_results.append({
                    "key": item["key"],
                    "value": result,
                    "call_id": call_id
                })

        # Perform single batch mutation to Hasura
        if batch_results:
            hasura_objects = [
                {
                    "key": entry["key"],
                    "value": entry["value"],
                    "call_id": entry["call_id"],
                    "type": "external"
                } for entry in batch_results
            ]
            print(f"📤 Inserting {len(hasura_objects)} prompt results to Hasura...")
            insert_multiple_call_data(hasura_objects)
            print(f"✅ Batch inserted to Hasura")

        return len(batch_results)

    # ThreadPoolExecutor for batching
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(process_batch, offset * batch_size)
            for offset in range(loop_count)
        ]
        total_prompts = 0
        for future in as_completed(futures):
            total_prompts += future.result()

    print(f"\n🎉 All calls processed in {time.time() - start_total:.2f}s")
    return {
        "message": f"Processed {total_calls} calls and inserted {total_prompts} prompts."
    }
