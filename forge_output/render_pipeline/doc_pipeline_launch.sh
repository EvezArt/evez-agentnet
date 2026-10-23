#!/bin/bash
# launcher — fully detaches the pipeline from any session tree.
setsid nohup bash /root/evez-agentnet/forge_output/render_pipeline/doc_pipeline.sh \
  >> /root/evez-agentnet/forge_output/render_pipeline/pipeline.log 2>&1 < /dev/null &
disown
echo "pipeline detached, log: /root/evez-agentnet/forge_output/render_pipeline/pipeline.log"
