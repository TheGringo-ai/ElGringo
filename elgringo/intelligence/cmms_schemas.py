#!/usr/bin/env python3
"""
CMMS Vendor Schema Definitions
==============================
Comprehensive field mappings for 15+ major CMMS vendors.

This module enables the Universal Ingestor to automatically recognize
and map columns from ANY CMMS export to our golden schema.

Vendors Covered:
- IBM Maximo
- SAP PM (Plant Maintenance)
- Infor EAM
- UpKeep
- Fiix (Rockwell)
- eMaint (Fluke)
- Limble CMMS
- Maintenance Connection
- FMX
- Hippo CMMS
- MPulse
- MicroMain
- Dude Solutions / Brightly
- ServiceChannel
- Generic/Common

Sources:
- https://databasesample.com/database/ibm-maximo-database
- https://www.se80.co.uk/sapmodules/p/pm-t/pm-tables-all.htm
- https://developers.onupkeep.com/
- https://fiixlabs.github.io/api-documentation/
- https://developer.servicechannel.com/
- https://apidocs.limblecmms.com/
"""

from typing import Dict, List, Set


# =============================================================================
# VENDOR-SPECIFIC FIELD MAPPINGS
# =============================================================================

IBM_MAXIMO_FIELDS = {
    # Work Order Fields
    "WONUM": "Work_Order_Number",
    "WORKORDERID": "Work_Order_Number",
    "SITEID": "Site_ID",
    "ASSETNUM": "Asset_ID",
    "LOCATION": "Location",
    "DESCRIPTION": "Description",
    "STATUS": "Status",
    "WORKTYPE": "Work_Type_ID",
    "PRIORITY": "Priority",
    "SCHEDSTART": "Scheduled_Start",
    "SCHEDFINISH": "Scheduled_Finish",
    "ACTSTART": "Actual_Start",
    "ACTFINISH": "Date_Completed",
    "TARGSTARTDATE": "Target_Start",
    "TARGCOMPDATE": "Date_Due",
    "REPORTDATE": "Created_Date",
    "REPORTEDBY": "Requested_By",
    "SUPERVISOR": "Assigned_Name",
    "ESTLABHRS": "Estimated_Hours",
    "ACTLABHRS": "Hours",
    "ESTLABCOST": "Estimated_Labor_Cost",
    "ACTLABCOST": "Labor_Cost",
    "ESTMATCOST": "Estimated_Part_Cost",
    "ACTMATCOST": "PartCosts",
    "ESTTOOLCOST": "Estimated_Tool_Cost",
    "ACTTOOLCOST": "Tool_Cost",
    "ESTSERVCOST": "Estimated_Service_Cost",
    "ACTSERVCOST": "Service_Cost",
    "ESTTOTALCOST": "Estimated_Total_Cost",
    "ACTTOTALCOST": "Total_Cost",
    "PMNUM": "PM_ID",
    "JPNUM": "Job_Plan",
    "PARENT": "Parent_WO",
    "PROBLEMCODE": "Problem_Code",
    "FAILURECODE": "Failure_Code",
    "GLDEBITACCT": "GL_Account",
    "CONTRACT": "Contract",
    "INSPECTOR": "Inspector",
    "OWNER": "Owner",
    "OWNERGROUP": "Owner_Group",
    "VENDOR": "Vendor",
    "WOPRIORITY": "Priority",
    "WO_STATUS": "Status",
    "WO_DESC": "Description",
}

SAP_PM_FIELDS = {
    # Order Tables (AUFK, AFKO, AFIH)
    "AUFNR": "Work_Order_Number",
    "AUART": "Work_Type_ID",
    "EQUNR": "Asset_ID",
    "TPLNR": "Location",
    "IWERK": "Plant",
    "KOSTV": "Cost_Center",
    "GSBER": "Business_Area",
    "ERDAT": "Created_Date",
    "ERNAM": "Created_By",
    "AEDAT": "Modified_Date",
    "GSTRP": "Scheduled_Start",
    "GLTRP": "Scheduled_Finish",
    "FTRMI": "Date_Due",
    "GETRI": "Date_Completed",
    "OBJNR": "Object_Number",
    "AUFPL": "Operation_List",
    "PRIESSION": "Priority",
    # Equipment Master (EQUI)
    "EQKTX": "Asset_Description",
    "EQTYP": "Asset_Type",
    "HERST": "Manufacturer",
    "TYPBZ": "Model",
    "SERGE": "Serial_Number",
    "INBDT": "Install_Date",
    "GEWRK": "Work_Center",
    # Notification (QMEL)
    "QMNUM": "Notification_Number",
    "QMART": "Notification_Type",
    "QMTXT": "Description",
    "ERZEIT": "Created_Time",
    "STRMN": "Required_Start",
    "STRUR": "Required_End",
    "LTRMN": "Required_End",
    # Functional Location (IFLOT)
    "TPLMA": "Parent_Location",
    "PLTXT": "Location_Description",
}

UPKEEP_FIELDS = {
    # Work Orders
    "id": "Work_Order_ID",
    "workOrderNo": "Work_Order_Number",
    "title": "Description",
    "description": "Purpose",
    "status": "Status",
    "priority": "Priority",
    "dueDate": "Date_Due",
    "endDueDate": "End_Due_Date",
    "dateCompleted": "Date_Completed",
    "createdAt": "Created_Date",
    "category": "Work_Type_ID",
    "time": "Hours",
    "cost": "Total_Cost",
    "assetId": "Asset_ID",
    "asset": "Asset_Description",
    "locationId": "Location_ID",
    "location": "Location",
    "assignedToId": "Assigned_ID",
    "assignedTo": "Assigned_Name",
    "assignedById": "Assigned_By_ID",
    "assignedBy": "Assigned_By",
    "completedById": "Completed_By_ID",
    "completedBy": "Completed_By",
    "requestedById": "Requested_By_ID",
    "requestedBy": "Requested_By",
    "teamId": "Team_ID",
    "team": "Team",
    "additionalInfo": "Notes",
    # Assets
    "name": "Asset_Description",
    "serial": "Barcode",
    "serialNumber": "Serial_Number",
    "model": "Model",
    "purchaseDate": "Purchase_Date",
    "placedInServiceDate": "Install_Date",
    "warrantyExpiration": "Warranty_End",
    "purchasePrice": "Purchase_Price",
    "parentAsset": "Parent_Asset",
    "manufacturerVendor": "Manufacturer",
    "downtimeStatus": "Downtime_Status",
}

FIIX_FIELDS = {
    # Work Orders
    "id": "Work_Order_ID",
    "strCode": "Work_Order_Number",
    "strDescription": "Description",
    "intPriorityID": "Priority",
    "intWorkOrderStatusID": "Status",
    "intSiteID": "Site_ID",
    "intAssetID": "Asset_ID",
    "intAssignedToUserID": "Assigned_ID",
    "dtmDateCreated": "Created_Date",
    "dtmDateCompleted": "Date_Completed",
    "dtmSuggestedCompletionDate": "Date_Due",
    "dblTimeEstimatedHours": "Estimated_Hours",
    "dblTimeSpentHours": "Hours",
    "dblLaborCost": "Labor_Cost",
    "dblPartsCost": "PartCosts",
    "dblTotalCost": "Total_Cost",
    "intWorkOrderTypeID": "Work_Type_ID",
    "intMaintenanceTypeID": "Maintenance_Type",
    # Assets
    "strName": "Asset_Description",
    "strSerialNumber": "Serial_Number",
    "strMake": "Manufacturer",
    "strModel": "Model",
    "dtmDatePurchased": "Purchase_Date",
    "dblPurchasePrice": "Purchase_Price",
}

SERVICECHANNEL_FIELDS = {
    # Work Orders
    "Id": "Work_Order_ID",
    "Number": "Work_Order_Number",
    "LocationId": "Location_ID",
    "LocationName": "Location",
    "ProviderId": "Provider_ID",
    "ProviderName": "Vendor",
    "Status": "Status",
    "Category": "Work_Type_ID",
    "Priority": "Priority",
    "Nte": "Not_To_Exceed",
    "CallDate": "Created_Date",
    "Description": "Description",
    "ProblemCode": "Problem_Code",
    "AreaId": "Area_ID",
    "AssetType": "Asset_Type",
    "AssetId": "Asset_ID",
    "CompletedDate": "Date_Completed",
    "ExpirationDate": "Date_Due",
    "RecallWorkOrder": "Parent_WO",
    # Assets
    "Tag": "Asset_Tag",
    "AssetTypeId": "Asset_Type_ID",
    "TradeId": "Trade_ID",
    "BrandId": "Brand_ID",
    "Active": "Active",
    "AssetTag": "Barcode",
    "AssetStatus": "Asset_Status",
}

LIMBLE_FIELDS = {
    # Tasks (Work Orders)
    "taskId": "Work_Order_ID",
    "taskName": "Description",
    "taskDescription": "Purpose",
    "taskStatus": "Status",
    "taskPriority": "Priority",
    "dueDate": "Date_Due",
    "completedDate": "Date_Completed",
    "createdDate": "Created_Date",
    "estimatedTime": "Estimated_Hours",
    "actualTime": "Hours",
    "laborCost": "Labor_Cost",
    "partsCost": "PartCosts",
    "totalCost": "Total_Cost",
    "assetId": "Asset_ID",
    "assetName": "Asset_Description",
    "locationId": "Location_ID",
    "locationName": "Location",
    "assignedUserId": "Assigned_ID",
    "assignedUserName": "Assigned_Name",
    # Assets
    "serialNumber": "Serial_Number",
    "manufacturer": "Manufacturer",
    "modelNumber": "Model",
    "purchaseDate": "Purchase_Date",
    "purchaseCost": "Purchase_Price",
    "warrantyExpiration": "Warranty_End",
    "parentAssetId": "Parent_Asset",
}

EMAINT_FIELDS = {
    # Work Orders
    "wo_number": "Work_Order_Number",
    "wo_description": "Description",
    "wo_status": "Status",
    "wo_priority": "Priority",
    "wo_type": "Work_Type_ID",
    "equipment_id": "Asset_ID",
    "equipment_name": "Asset_Description",
    "location": "Location",
    "assigned_to": "Assigned_Name",
    "requested_by": "Requested_By",
    "date_opened": "Created_Date",
    "date_due": "Date_Due",
    "date_completed": "Date_Completed",
    "est_hours": "Estimated_Hours",
    "actual_hours": "Hours",
    "labor_cost": "Labor_Cost",
    "parts_cost": "PartCosts",
    "total_cost": "Total_Cost",
    # Assets
    "equip_id": "Asset_ID",
    "equip_desc": "Asset_Description",
    "serial_no": "Serial_Number",
    "model_no": "Model",
    "mfg": "Manufacturer",
}

HIPPO_FIELDS = {
    # Work Orders
    "WorkOrderNumber": "Work_Order_Number",
    "WorkOrderDescription": "Description",
    "WorkOrderStatus": "Status",
    "WorkOrderPriority": "Priority",
    "WorkOrderType": "Work_Type_ID",
    "AssetID": "Asset_ID",
    "AssetName": "Asset_Description",
    "LocationID": "Location_ID",
    "LocationName": "Location",
    "AssignedTo": "Assigned_Name",
    "RequestedBy": "Requested_By",
    "DateCreated": "Created_Date",
    "DateDue": "Date_Due",
    "DateCompleted": "Date_Completed",
    "EstimatedHours": "Estimated_Hours",
    "ActualHours": "Hours",
    "LaborCost": "Labor_Cost",
    "PartsCost": "PartCosts",
    "TotalCost": "Total_Cost",
}

MPULSE_FIELDS = {
    # Work Orders
    "WONumber": "Work_Order_Number",
    "WODescription": "Description",
    "WOStatus": "Status",
    "WOPriority": "Priority",
    "WOType": "Work_Type_ID",
    "EquipmentID": "Asset_ID",
    "EquipmentName": "Asset_Description",
    "Location": "Location",
    "AssignedTech": "Assigned_Name",
    "Requester": "Requested_By",
    "OpenDate": "Created_Date",
    "DueDate": "Date_Due",
    "CloseDate": "Date_Completed",
    "EstHours": "Estimated_Hours",
    "ActHours": "Hours",
    "LaborCost": "Labor_Cost",
    "MaterialCost": "PartCosts",
    "TotalCost": "Total_Cost",
}

MAINTENANCE_CONNECTION_FIELDS = {
    # Work Orders
    "WorkOrder": "Work_Order_Number",
    "WO_Number": "Work_Order_Number",
    "Description": "Description",
    "Status": "Status",
    "Priority": "Priority",
    "Type": "Work_Type_ID",
    "Asset": "Asset_ID",
    "AssetDescription": "Asset_Description",
    "Location": "Location",
    "Technician": "Assigned_Name",
    "TechnicianName": "Assigned_Name",
    "Requester": "Requested_By",
    "RequesterName": "Requested_By",
    "Authorizer": "Authorized_By",
    "DateOpened": "Created_Date",
    "DateRequested": "Created_Date",
    "DateDue": "Date_Due",
    "RequestedCompletionDate": "Date_Due",
    "DateClosed": "Date_Completed",
    "DateCompleted": "Date_Completed",
    "EstimatedHours": "Estimated_Hours",
    "ActualHours": "Hours",
    "LaborCost": "Labor_Cost",
    "PartsCost": "PartCosts",
    "TotalCost": "Total_Cost",
}

BRIGHTLY_FIELDS = {
    # Work Orders (SchoolDude, FacilityDude, TheWorxHub)
    "RequestID": "Work_Order_Number",
    "RequestNumber": "Work_Order_Number",
    "RequestDescription": "Description",
    "ProblemDescription": "Purpose",
    "RequestStatus": "Status",
    "Priority": "Priority",
    "RequestType": "Work_Type_ID",
    "AssetID": "Asset_ID",
    "AssetName": "Asset_Description",
    "BuildingID": "Location_ID",
    "BuildingName": "Location",
    "RoomNumber": "Room",
    "AssignedTo": "Assigned_Name",
    "Requestor": "Requested_By",
    "RequestorName": "Requested_By",
    "DateSubmitted": "Created_Date",
    "DateNeeded": "Date_Due",
    "DateCompleted": "Date_Completed",
    "EstimatedTime": "Estimated_Hours",
    "ActualTime": "Hours",
    "LaborCost": "Labor_Cost",
    "MaterialCost": "PartCosts",
    "TotalCost": "Total_Cost",
}

INFOR_EAM_FIELDS = {
    # Work Orders
    "workordernum": "Work_Order_Number",
    "workordernumber": "Work_Order_Number",
    "description": "Description",
    "status": "Status",
    "priority": "Priority",
    "workordertype": "Work_Type_ID",
    "equipment": "Asset_ID",
    "equipmentdesc": "Asset_Description",
    "location": "Location",
    "assignedto": "Assigned_Name",
    "reportedby": "Requested_By",
    "datecreated": "Created_Date",
    "targetdate": "Date_Due",
    "completeddate": "Date_Completed",
    "estimatedhours": "Estimated_Hours",
    "actualhours": "Hours",
    "laborcost": "Labor_Cost",
    "materialcost": "PartCosts",
    "totalcost": "Total_Cost",
    "department": "Department",
    "costcenter": "Cost_Center",
}


# =============================================================================
# COMBINED FIELD ALIAS DICTIONARY
# =============================================================================

def build_comprehensive_aliases() -> Dict[str, List[str]]:
    """
    Build a comprehensive alias dictionary combining all vendor mappings.

    Returns:
        Dict mapping golden field names to list of known aliases
    """
    # Start with base aliases
    aliases = {
        # Work Order Identification
        "Work_Order_Number": [
            # IBM Maximo
            "wonum", "workorderid", "wo_num", "wo_number", "wono",
            # SAP PM
            "aufnr", "order_number", "orderno",
            # UpKeep
            "workorderno", "work_order_no",
            # Fiix
            "strcode",
            # ServiceChannel
            "number",
            # Limble
            "taskid",
            # Generic
            "work_order", "workorder", "wo", "wo#", "order", "order_no",
            "order_id", "orderid", "request_number", "requestnumber",
            "request_id", "requestid", "ticket", "ticket_number", "ticketno",
        ],

        # Asset Identification
        "Asset_ID": [
            # IBM Maximo
            "assetnum", "asset_num",
            # SAP PM
            "equnr", "equipment_number", "equipmentnumber",
            # UpKeep
            "assetid",
            # Fiix
            "intassetid",
            # ServiceChannel
            "assetid",
            # Generic
            "asset", "asset_no", "assetno", "asset_code", "assetcode",
            "equipment_id", "equipmentid", "equip_id", "equipid",
            "equipment", "equip", "machine_id", "machineid", "machine",
            "asset_tag", "assettag", "tag", "equipment_tag", "equiptag",
            "unit_id", "unitid", "unit",
        ],

        # Asset Description
        "Asset_Description": [
            # IBM Maximo
            "description",
            # SAP PM
            "eqktx", "equipment_description",
            # UpKeep
            "asset", "name", "assetname",
            # Fiix
            "strname",
            # Generic
            "asset_desc", "assetdesc", "asset_name", "assetname",
            "equipment_name", "equipmentname", "equip_name", "equipname",
            "equipment_desc", "equipmentdesc", "equip_desc", "equipdesc",
            "machine_name", "machinename", "machine_desc", "machinedesc",
            "unit_name", "unitname", "unit_desc", "unitdesc",
        ],

        # Description / Purpose
        "Description": [
            # IBM Maximo
            "description", "wo_desc",
            # SAP PM
            "qmtxt",
            # UpKeep
            "title",
            # Fiix
            "strdescription",
            # Generic
            "work_description", "workdescription", "wo_description",
            "task_description", "taskdescription", "problem_description",
            "job_description", "jobdescription", "summary", "subject",
            "issue", "problem", "request",
        ],

        "Purpose": [
            "purpose", "reason", "cause", "notes", "comments",
            "additional_info", "additionalinfo", "details",
            "work_requested", "workrequested",
        ],

        # Status
        "Status": [
            # IBM Maximo
            "status", "wo_status",
            # SAP PM
            "status",
            # UpKeep
            "status",
            # Generic
            "work_order_status", "workorderstatus", "wo_status", "wostatus",
            "order_status", "orderstatus", "request_status", "requeststatus",
            "state", "condition", "status_id", "statusid", "status_code",
        ],

        # Work Type
        "Work_Type_ID": [
            # IBM Maximo
            "worktype", "work_type",
            # SAP PM
            "auart", "order_type",
            # UpKeep
            "category",
            # Generic
            "work_type_id", "worktypeid", "wo_type", "wotype",
            "type", "job_type", "jobtype", "task_type", "tasktype",
            "maintenance_type", "maintenancetype", "maint_type", "mainttype",
            "service_type", "servicetype", "request_type", "requesttype",
            "order_type", "ordertype", "work_category", "workcategory",
        ],

        # Dates
        "Date_Completed": [
            # IBM Maximo
            "actfinish", "actual_finish",
            # SAP PM
            "getri",
            # UpKeep
            "datecompleted", "date_completed",
            # Generic
            "completed_date", "completeddate", "completion_date", "completiondate",
            "finish_date", "finishdate", "end_date", "enddate",
            "close_date", "closedate", "closed_date", "closeddate",
            "actual_end", "actualend", "actual_finish_date", "actualfinishdate",
            "done_date", "donedate",
        ],

        "Date_Due": [
            # IBM Maximo
            "targcompdate", "target_completion",
            # SAP PM
            "ftrmi", "gltrp",
            # UpKeep
            "duedate", "due_date",
            # Generic
            "target_date", "targetdate", "scheduled_completion",
            "required_date", "requireddate", "need_by", "needby",
            "needed_by", "neededby", "expected_date", "expecteddate",
            "deadline", "sla_date", "sladate",
        ],

        "Created_Date": [
            # IBM Maximo
            "reportdate", "report_date",
            # SAP PM
            "erdat",
            # UpKeep
            "createdat", "created_at",
            # Generic
            "creation_date", "creationdate", "open_date", "opendate",
            "opened_date", "openeddate", "request_date", "requestdate",
            "submit_date", "submitdate", "submitted_date", "submitteddate",
            "entry_date", "entrydate", "input_date", "inputdate",
            "date_created", "datecreated", "date_opened", "dateopened",
        ],

        "Scheduled_Start": [
            # IBM Maximo
            "schedstart", "scheduled_start",
            # SAP PM
            "gstrp",
            # Generic
            "start_date", "startdate", "planned_start", "plannedstart",
            "target_start", "targetstart", "schedule_start", "schedulestart",
        ],

        # Hours
        "Hours": [
            # IBM Maximo
            "actlabhrs", "actual_labor_hours",
            # UpKeep
            "time",
            # Fiix
            "dbltimespenthours",
            # Generic
            "actual_hours", "actualhours", "hours_worked", "hoursworked",
            "labor_hours", "laborhours", "work_hours", "workhours",
            "time_spent", "timespent", "duration", "total_hours", "totalhours",
        ],

        "Estimated_Hours": [
            # IBM Maximo
            "estlabhrs", "estimated_labor_hours",
            # Fiix
            "dbltimeestimatedhours",
            # Generic
            "est_hours", "esthours", "planned_hours", "plannedhours",
            "budgeted_hours", "budgetedhours", "expected_hours", "expectedhours",
        ],

        # Costs
        "PartCosts": [
            # IBM Maximo
            "actmatcost", "actual_material_cost",
            # Fiix
            "dblpartscost",
            # Generic
            "parts_cost", "partscost", "part_cost", "partcost",
            "material_cost", "materialcost", "materials_cost", "materialscost",
            "parts", "materials", "inventory_cost", "inventorycost",
        ],

        "Labor_Cost": [
            # IBM Maximo
            "actlabcost", "actual_labor_cost",
            # Fiix
            "dbllaborcost",
            # Generic
            "labor_cost", "laborcost", "labour_cost", "labourcost",
            "work_cost", "workcost", "technician_cost", "techniciancost",
        ],

        "Total_Cost": [
            # IBM Maximo
            "acttotalcost", "actual_total_cost",
            # UpKeep
            "cost",
            # Fiix
            "dbltotalcost",
            # Generic
            "total_cost", "totalcost", "total", "cost_total", "costtotal",
            "wo_cost", "wocost", "order_cost", "ordercost",
            "total_amount", "totalamount", "amount",
        ],

        # People
        "Assigned_Name": [
            # IBM Maximo
            "supervisor",
            # UpKeep
            "assignedto", "assigned_to",
            # Generic
            "technician", "tech", "assigned", "assignee",
            "assigned_technician", "assignedtechnician",
            "assigned_to_name", "assignedtoname",
            "worker", "mechanic", "craftsperson", "craftsman",
            "labor_code", "laborcode", "emp_name", "empname",
            "employee_name", "employeename", "resource",
        ],

        "Requested_By": [
            # IBM Maximo
            "reportedby", "reported_by",
            # UpKeep
            "requestedby", "requested_by",
            # Generic
            "requester", "requestor", "caller", "reporter",
            "submitted_by", "submittedby", "opened_by", "openedby",
            "created_by", "createdby", "originator", "initiator",
            "contact", "contact_name", "contactname",
        ],

        # Location
        "Location": [
            # IBM Maximo
            "location",
            # SAP PM
            "tplnr", "functional_location",
            # UpKeep
            "location",
            # Generic
            "loc", "site", "building", "facility", "area",
            "location_name", "locationname", "location_desc", "locationdesc",
            "loc_id", "locid", "site_id", "siteid", "plant",
            "department", "dept", "zone", "section", "room",
        ],

        # Entity / Organization
        "Entity_Name": [
            "entity", "entity_name", "entityname", "organization",
            "org", "company", "client", "customer", "account",
            "business_unit", "businessunit", "division",
        ],

        # Priority
        "Priority": [
            # IBM Maximo
            "priority", "wopriority",
            # Generic
            "priority_level", "prioritylevel", "urgency",
            "priority_code", "prioritycode", "priority_id", "priorityid",
            "importance", "severity", "criticality",
        ],

        # PM Reference
        "PM_ID": [
            # IBM Maximo
            "pmnum", "pm_number",
            # Generic
            "pm_id", "pmid", "pm", "preventive_maintenance",
            "pm_schedule", "pmschedule", "schedule_id", "scheduleid",
            "pm_template", "pmtemplate",
        ],

        # Problem/Failure Codes
        "Problem_Code": [
            # IBM Maximo
            "problemcode", "problem_code",
            # ServiceChannel
            "problemcode",
            # Generic
            "failure_code", "failurecode", "issue_code", "issuecode",
            "symptom_code", "symptomcode", "cause_code", "causecode",
            "reason_code", "reasoncode", "defect_code", "defectcode",
        ],

        # Serial/Model
        "Serial_Number": [
            # SAP PM
            "serge",
            # UpKeep
            "serialnumber", "serial_number",
            # Generic
            "serial", "sn", "serial_no", "serialno",
        ],

        "Model": [
            # SAP PM
            "typbz",
            # UpKeep
            "model",
            # Generic
            "model_number", "modelnumber", "model_no", "modelno",
            "model_name", "modelname",
        ],

        "Manufacturer": [
            # SAP PM
            "herst",
            # UpKeep
            "manufacturervendor",
            # Generic
            "manufacturer", "mfg", "mfr", "make", "brand", "vendor",
            "oem", "supplier",
        ],
    }

    # Add vendor-specific mappings (reverse mapping)
    vendor_maps = [
        IBM_MAXIMO_FIELDS,
        SAP_PM_FIELDS,
        UPKEEP_FIELDS,
        FIIX_FIELDS,
        SERVICECHANNEL_FIELDS,
        LIMBLE_FIELDS,
        EMAINT_FIELDS,
        HIPPO_FIELDS,
        MPULSE_FIELDS,
        MAINTENANCE_CONNECTION_FIELDS,
        BRIGHTLY_FIELDS,
        INFOR_EAM_FIELDS,
    ]

    for vendor_map in vendor_maps:
        for vendor_field, golden_field in vendor_map.items():
            if golden_field in aliases:
                vendor_lower = vendor_field.lower()
                if vendor_lower not in aliases[golden_field]:
                    aliases[golden_field].append(vendor_lower)

    return aliases


# Build the comprehensive alias dictionary
COMPREHENSIVE_ALIASES = build_comprehensive_aliases()


def get_all_known_fields() -> Set[str]:
    """Get all known field names across all vendors."""
    all_fields = set()
    for aliases in COMPREHENSIVE_ALIASES.values():
        all_fields.update(aliases)
    return all_fields


def identify_vendor(columns: List[str]) -> str:
    """
    Attempt to identify the CMMS vendor based on column names.

    Args:
        columns: List of column names from CSV

    Returns:
        Vendor name or "Unknown"
    """
    columns_lower = [c.lower() for c in columns]

    # Check for vendor-specific signatures
    vendor_signatures = {
        "IBM Maximo": ["wonum", "assetnum", "actlabhrs", "pmnum", "jpnum"],
        "SAP PM": ["aufnr", "equnr", "tplnr", "iwerk", "erdat"],
        "UpKeep": ["workorderno", "datecompleted", "createdat", "assetid"],
        "Fiix": ["strcode", "strdescription", "intassetid", "dbltotalcost"],
        "ServiceChannel": ["locationid", "providerid", "nte", "calldate"],
        "Limble": ["taskid", "taskname", "taskstatus", "taskpriority"],
        "eMaint": ["wo_number", "equipment_id", "date_opened", "equip_id"],
        "Hippo": ["workordernumber", "workorderstatus", "workorderpriority"],
        "MPulse": ["wonumber", "equipmentid", "assignedtech", "opendate"],
        "Brightly": ["requestid", "requestnumber", "requeststatus", "buildingid"],
        "Infor EAM": ["workordernum", "equipmentdesc", "targetdate"],
    }

    for vendor, signatures in vendor_signatures.items():
        matches = sum(1 for sig in signatures if sig in columns_lower)
        if matches >= 2:  # At least 2 signature fields
            return vendor

    return "Unknown"


def get_vendor_fields(vendor: str) -> Dict[str, str]:
    """Get field mappings for a specific vendor."""
    vendor_maps = {
        "IBM Maximo": IBM_MAXIMO_FIELDS,
        "SAP PM": SAP_PM_FIELDS,
        "UpKeep": UPKEEP_FIELDS,
        "Fiix": FIIX_FIELDS,
        "ServiceChannel": SERVICECHANNEL_FIELDS,
        "Limble": LIMBLE_FIELDS,
        "eMaint": EMAINT_FIELDS,
        "Hippo": HIPPO_FIELDS,
        "MPulse": MPULSE_FIELDS,
        "Maintenance Connection": MAINTENANCE_CONNECTION_FIELDS,
        "Brightly": BRIGHTLY_FIELDS,
        "Infor EAM": INFOR_EAM_FIELDS,
    }
    return vendor_maps.get(vendor, {})
