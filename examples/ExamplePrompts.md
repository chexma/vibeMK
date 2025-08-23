# Some Tips for prompting

Be as precise as possible and add as much information as necesary to complete your task.

Add these sentences to your prompt to minimize fictional input values and avoid automatic creation of objects. 

- Don´t activate changes automatically.
- Ask if you are unsure.
- Ask for relevant input values, don´t assume information.

If in doubt, test all prompts in a test environment beforehand. Multiple checkmk instances can be connected.

# Examples

## Performance Metrics

1. Can you analyze the response_time metric of the “HTTPS Webservice” service of the host “www.google.de” for the last ten minutes in checkmk and display any anomalies? Focus on the most important things and give a brief explanation.

2. Can you compare the response_time metric of the “HTTPS Webservice” service of the host “www.google.de”  and host "www.heise.de" for the last ten minutes in checkmk and display any anomalies?

## Rulesets 

1. Can you check if there are duplicate rules or rules that could be combined in the ruleset Filesystems (used space and growth) in checkmk ?

## Folders

1. Create folders with the name and description of the three character airport codes of the ten largest countries in europe in checkmk, use the code for the id and the name of the folders. Don´t activate the changes.

2. Delete the folder that is exactly called Servers, if there is none, stop.

## Downtimes

1. Show all configured host and service downtimes

## Tags / Tag groups

1. Add a new tag group called location with the following tags:
location_cologne:Cologne
location_newyork:NewYork
location_shanghai:Shanghai

2. Add a new tag to the tag group location: location_saopaulo:Sao Paulo