/*! @file db/Net.cpp
    @brief Net class implementation
    @author anoynmous anoynmous
    @date 11/24/2018
*/
#include "db/Net.h"
#include <set>

PROJECT_NAMESPACE_BEGIN

/*! A set of possible power net names. */
static const std::set<std::string> POWER_NET_NAMES = {"vdd", "VDD", "Vdd", "VDDA", "vdda", "Vdda", "vcc", "AVDD"};
/*! A set of possible ground net names. */
static const std::set<std::string> GROUND_NET_NAMES = {"vss", "VSS", "Vss", "VSSA", "vssa", "Vssa", "gnd", "Gnd", "GND", "AVSS"};

/*! Return netType of net based on name. 
    Currently supported Power/Ground names 
    are limited to conventional VDD/VSS.
    Add unsupported names for Power/Ground
    filtering to POWER_NET_NAMES and 
    GROUND_NET_NAMES to /db/Net.cpp.
*/ 
NetType Net::netType() const
{
    if ( POWER_NET_NAMES.count(_name) )
        return NetType::POWER;
    if ( GROUND_NET_NAMES.count(_name) ) 
        return NetType::GROUND; 
    return NetType::SIGNAL;
}

PROJECT_NAMESPACE_END