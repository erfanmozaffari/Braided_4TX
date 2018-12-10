#include "opendefs.h"
#include "uinject.h"
#include "openqueue.h"
#include "openserial.h"
#include "packetfunctions.h"
#include "scheduler.h"
#include "IEEE802154E.h"
#include "idmanager.h"

//=========================== variables =======================================

uinject_vars_t uinject_vars;

static const uint8_t uinject_payload[]    = "uinject";
static const uint8_t uinject_dst_addr[]   = {
   0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01
}; 

//=========================== prototypes ======================================

void uinject_timer_cb(opentimers_id_t id);
void uinject_task_cb(void);

//=========================== public ==========================================

void uinject_init() {
   
    // clear local variables
    memset(&uinject_vars,0,sizeof(uinject_vars_t));

    // register at UDP stack
    uinject_vars.desc.port              = WKP_UDP_INJECT;
    uinject_vars.desc.callbackReceive   = &uinject_receive;
    uinject_vars.desc.callbackSendDone  = &uinject_sendDone;
    openudp_register(&uinject_vars.desc);

    uinject_vars.timerId = opentimers_create();
#ifdef QUEUE_MANAGEMENT
    // start periodic timer
    uinject_vars.period = uinject_loadStartingOfFlow()+(SCHEDULE_MINIMAL_6TISCH_ACTIVE_CELLS+NUMSERIALRX-1);
    /*opentimers_scheduleIn(
        uinject_vars.timerId,
        15,   // one slot duration: 15ms
        TIME_MS,
        TIMER_PERIODIC,
        uinject_timer_cb
    );*/

    opentimers_scheduleIn(
        uinject_vars.timerId,
        340*SLOTFRAME_LENGTH*15,   // one slot duration: 15ms, it is around 4 minutes
        TIME_MS,
        TIMER_ONESHOT,
        uinject_timer_cb
    );
#else
    // start periodic timer 
    uinject_vars.period = UINJECT_PERIOD_MS;
    opentimers_scheduleIn(
        uinject_vars.timerId,
        uinject_vars.period,
        TIME_MS,
        TIMER_PERIODIC,
        uinject_timer_cb
    );
#endif

}

void uinject_sendDone(OpenQueueEntry_t* msg, owerror_t error) {
   openqueue_freePacketBuffer(msg);
}

void uinject_receive(OpenQueueEntry_t* pkt) {
   
   openqueue_freePacketBuffer(pkt);
   
   openserial_printError(
      COMPONENT_UINJECT,
      ERR_RCVD_ECHO_REPLY,
      (errorparameter_t)0,
      (errorparameter_t)0
   );
}

//=========================== private =========================================

/**
\note timer fired, but we don't want to execute task in ISR mode instead, push
   task to scheduler with CoAP priority, and let scheduler take care of it.
*/
void uinject_timer_cb(opentimers_id_t id){
#ifdef QUEUE_MANAGEMENT
    // start periodic timer
    opentimers_scheduleIn(
        uinject_vars.timerId,
        15,   // one slot duration: 15ms
        TIME_MS,
        TIMER_PERIODIC,
        uinject_timer_cb
    );
#endif
   scheduler_push_task(uinject_task_cb,TASKPRIO_COAP);
}

void uinject_task_cb() {
   OpenQueueEntry_t*    pkt;
   uint8_t              asnArray[5];

   // don't run if not synch
   if (ieee154e_isSynch() == FALSE) return;
   
   // don't run on dagroot
   if (idmanager_getIsDAGroot()) {
      opentimers_destroy(uinject_vars.timerId);
      return;
   }

#ifdef QUEUE_MANAGEMENT  
   ieee154e_getAsn(asnArray);
   uint32_t currentASN = asnArray[0] + asnArray[1]*256 + asnArray[2]*256*256 + asnArray[3]*256*256*256;
   if (currentASN%SLOTFRAME_LENGTH!=uinject_vars.period)
   	  return;

   if (!openqueue_makeQueueEmpty(IANA_UDP, COMPONENT_UINJECT)) {
      return;
   }
#endif

   // if you get here, send a packet
   printf("Mote %d packet created on ASN %d\n", idmanager_getMyID(ADDR_64B)->addr_64b[7], currentASN);

   // get a free packet buffer
   pkt = openqueue_getFreePacketBuffer(COMPONENT_UINJECT);
   if (pkt==NULL) {
      openserial_printError(
         COMPONENT_UINJECT,
         ERR_NO_FREE_PACKET_BUFFER,
         (errorparameter_t)0,
         (errorparameter_t)0
      );
      return;
   }
   
   pkt->owner                         = COMPONENT_UINJECT;
   pkt->creator                       = COMPONENT_UINJECT;
   pkt->l4_protocol                   = IANA_UDP;
   pkt->l4_destination_port           = WKP_UDP_INJECT;
   pkt->l4_sourcePortORicmpv6Type     = WKP_UDP_INJECT;
   pkt->l3_destinationAdd.type        = ADDR_128B;
   memcpy(&pkt->l3_destinationAdd.addr_128b[0],uinject_dst_addr,16);
   
   // add payload
   packetfunctions_reserveHeaderSize(pkt,sizeof(uinject_payload)-1);
   memcpy(&pkt->payload[0],uinject_payload,sizeof(uinject_payload)-1);
   
   packetfunctions_reserveHeaderSize(pkt,sizeof(uint16_t));
   pkt->payload[1] = (uint8_t)((uinject_vars.counter & 0xff00)>>8);
   pkt->payload[0] = (uint8_t)(uinject_vars.counter & 0x00ff);
   uinject_vars.counter++;
   
   packetfunctions_reserveHeaderSize(pkt,sizeof(uint8_t));
   pkt->payload[0] = idmanager_getMyID(ADDR_64B)->addr_64b[7];

   packetfunctions_reserveHeaderSize(pkt,sizeof(asn_t));
   ieee154e_getAsn(asnArray);
   pkt->payload[0] = asnArray[0];
   pkt->payload[1] = asnArray[1];
   pkt->payload[2] = asnArray[2];
   pkt->payload[3] = asnArray[3];
   pkt->payload[4] = asnArray[4];
	
   if ((openudp_send(pkt))==E_FAIL) {
      openqueue_freePacketBuffer(pkt);
   }
}


#ifdef QUEUE_MANAGEMENT

uint8_t uinject_loadStartingOfFlow() {
   // don't run on dagroot
	if (idmanager_getMyID(ADDR_64B)->addr_64b[7] == 1)
		return 0;

	uint8_t moteId,startingSlotOffset=0,bufsize=0;
	bool found = FALSE;
	char *buffer, *p;
   FILE *file = fopen ("../../../logs_Topology/startOfFlows.txt", "r");
   //FILE *file = fopen ("startOfFlows.txt", "r");
   if (file != NULL) {      	
      while(!feof(file)) {
         getline(&buffer,&bufsize,file);
         p = strtok(buffer, " ");
         moteId = atoi(p);
         p = strtok(NULL, " ");
         startingSlotOffset = atoi(p);
         if (moteId == idmanager_getMyID(ADDR_64B)->addr_64b[7])
         	  break;
      }
      fclose (file);
   }
   return startingSlotOffset;
}

#endif